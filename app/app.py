import uuid, http
from flask import Flask, request, jsonify
from flasgger import Swagger
from redis_client import RedisClient
from config import (
    TOKEN_POOL_KEY, FREE_TOKEN_KEY_FORMAT, ASSIGNED_TOKEN_KEY_FORMAT, KEEP_ALIVE_INTERVAL,
    POOL_MAX_SIZE, TOKEN_LIFETIME, KEEP_ALIVE_BATCH_SIZE
)

app = Flask(__name__)
swagger = Swagger(app)
redisclient = RedisClient.get_client()


@app.route('/generate', methods=['POST'])
def generate_tokens():
    """
    Generate tokens
    ---
    tags:
      - Tokens
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            count:
              type: integer
              description: Number of tokens to generate
              example: 5
    responses:
      200:
        description: A list of generated tokens
        schema:
          type: object
          properties:
            tokens:
              type: array
              items:
                type: string
      400:
        description: Pool max size exceeded
    """

    count = int(request.json.get('count', 1))
    if redisclient.scard(TOKEN_POOL_KEY) + count > POOL_MAX_SIZE:
        return jsonify({"error": "Pool max size exceeded"}), http.HTTPStatus.BAD_REQUEST
    tokens = [str(uuid.uuid4()) for _ in range(count)]
    for token in tokens:
        redisclient.sadd(TOKEN_POOL_KEY, token)
        redisclient.set(FREE_TOKEN_KEY_FORMAT.format(token=token), "alive", ex=KEEP_ALIVE_INTERVAL)
    return jsonify({"tokens": tokens}), http.HTTPStatus.OK



@app.route('/assign', methods=['POST'])
def assign_token():
    """
    Assign a token from the pool
    ---
    tags:
      - Tokens
    responses:
      200:
        description: A token has been assigned
        schema:
          type: object
          properties:
            token:
              type: string
      404:
        description: No free token available or token TTL expired
    """

    lua_script = """
        local token = redis.call('spop', KEYS[1])
        if token then
            -- Check if the token's pool entry still exists
            if redis.call('exists', KEYS[2] .. token) == 1 then
                redis.call('set', KEYS[3] .. token, 'assigned', 'EX', ARGV[1])  -- Assign token with TTL
                return token
            else
                return nil  -- Token is no longer valid, don't assign it
            end
        end
        return nil  -- No token available in pool
    """
    assigned_token_key = ASSIGNED_TOKEN_KEY_FORMAT.replace("{token}", "")
    pool_token_key = FREE_TOKEN_KEY_FORMAT.replace("{token}", "")
    assigned_token = redisclient.eval(lua_script, 3, TOKEN_POOL_KEY, pool_token_key, assigned_token_key, TOKEN_LIFETIME)
    if assigned_token:
        return jsonify({"token": assigned_token}), http.HTTPStatus.OK

    return jsonify({"error": "No free token available or token TTL expired"}), http.HTTPStatus.NOT_FOUND

@app.route('/unblock', methods=['POST'])
def unblock_token():
    """
    Unblock a token
    ---
    tags:
      - Tokens
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            token:
              type: string
              description: The token to unblock
              example: "abc123"
    responses:
      200:
        description: Token unblocked successfully
      404:
        description: Token not found
      400:
        description: Token is a required field
    """

    token = request.json.get('token')
    if not token:
        return jsonify({"message": "Token is a required field"}), http.HTTPStatus.BAD_REQUEST
    
    lua_script = """
        local assigned_key = KEYS[3] .. ARGV[1]
        local pool_key = KEYS[2] .. ARGV[1]

        if redis.call('exists', assigned_key) == 1 then
            -- Token is assigned; unblock it
            redis.call('del', assigned_key)
            redis.call('sadd', KEYS[1], ARGV[1])
            redis.call('set', pool_key, 'alive', 'EX', ARGV[2])
            return {1, "Token " .. ARGV[1] .. " unblocked successfully"}
        else
            -- Token is not assigned; check if it's valid in the pool
            if redis.call('exists', pool_key) == 1 then
                return {0, "Token not assigned"}
            else
                return {0, "Token not found"}
            end
        end
    """
    assigned_token_key = ASSIGNED_TOKEN_KEY_FORMAT.replace("{token}", "")
    pool_token_key = FREE_TOKEN_KEY_FORMAT.replace("{token}", "")
    success, message = redisclient.eval(lua_script, 3, TOKEN_POOL_KEY, pool_token_key, assigned_token_key, token, KEEP_ALIVE_INTERVAL)
    
    if int(success):
        return jsonify({"message": message}), http.HTTPStatus.OK
    else:
        return jsonify({"error": message}), http.HTTPStatus.NOT_FOUND

@app.route('/delete', methods=['DELETE'])
def delete_token():
    """
    Delete a token
    ---
    tags:
      - Tokens
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            token:
              type: string
              description: The token to delete
              example: "abc123"
    responses:
      200:
        description: Token deleted successfully
      404:
        description: Token not found
      400:
        description: Token is a required field
    """

    token = request.json.get('token')
    if not token:
        return jsonify({"message": "Token is a required field"}), http.HTTPStatus.BAD_REQUEST
    
    lua_script = """
        local assigned_key = KEYS[3] .. ARGV[1]
        local pool_key = KEYS[2] .. ARGV[1]

        if redis.call('exists', assigned_key) == 1 or redis.call('exists', pool_key) == 1 then
            -- Token exists; delete it from all keyspaces
            redis.call('del', assigned_key)
            redis.call('del', pool_key)
            redis.call('srem', KEYS[1], ARGV[1])
            return {1, "Token " .. ARGV[1] .. " deleted successfully"}
        else
            -- Token is invalid
            return {0, "Token not found"}
        end
    """
    assigned_token_key = ASSIGNED_TOKEN_KEY_FORMAT.replace("{token}", "")
    pool_token_key = FREE_TOKEN_KEY_FORMAT.replace("{token}", "")
    success, message = redisclient.eval(lua_script, 3, TOKEN_POOL_KEY, pool_token_key, assigned_token_key, token)

    if int(success):
        return jsonify({"message": message}), http.HTTPStatus.OK
    else:
        return jsonify({"error": message}), http.HTTPStatus.NOT_FOUND


@app.route('/keep-alive', methods=['POST'])
def keep_alive():
    """
    Keep a token alive by extending its TTL
    ---
    tags:
      - Tokens
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            token:
              type: string
              description: The token to keep alive
              example: "abc123"
              optional: true
    responses:
      200:
        description: Token TTL extended successfully
      404:
        description: Token not found
    """

    token = request.json.get('token')
    
    # Making token an optional parameter
    # If token is not provided in the request, then update keep-alive time for all tokens in the pool
    if not token:
        lua_script = """
            local keys_pattern = KEYS[1]
            local expiry_time = tonumber(ARGV[1])
            local batch_size = ARGV[2]
            local cursor = "0"
            local count = 0  -- Counter for successfully set expiry

            repeat
                -- Scan the keys matching the pattern
                local result = redis.call("SCAN", cursor, "MATCH", keys_pattern, "COUNT", batch_size)
                cursor = result[1]
                local keys = result[2]

                -- Iterate through the matched keys and set expiry
                for _, key in ipairs(keys) do
                    local success = redis.call("EXPIRE", key, expiry_time)
                    if success == 1 then
                        count = count + 1  -- Increment count for successful expiry
                    end
                end
            until cursor == "0"

            -- Return the count of keys with successfully set expiry
            return count
        """
        success_cnt = redisclient.eval(lua_script, 1, FREE_TOKEN_KEY_FORMAT.format(token="*"), KEEP_ALIVE_INTERVAL, KEEP_ALIVE_BATCH_SIZE)
        return jsonify({"message": f"TTL extended successfully for {success_cnt} tokens"}), http.HTTPStatus.OK
        
    # Else if token is provided just update the TTL for that token
    else:
        # If token found in the assigned keyspace, increase its TTL by configured token lifetime
        if redisclient.exists(ASSIGNED_TOKEN_KEY_FORMAT.format(token=token)):
            redisclient.expire(ASSIGNED_TOKEN_KEY_FORMAT.format(token=token), TOKEN_LIFETIME)
            return jsonify({"message": f"Assigned token {token} TTL extended successfully"}), http.HTTPStatus.OK

        # Else token found in pool keyspace, increase its TTL by configured keep alive time
        elif redisclient.exists(FREE_TOKEN_KEY_FORMAT.format(token=token)):
            redisclient.expire(FREE_TOKEN_KEY_FORMAT.format(token=token), KEEP_ALIVE_INTERVAL)
            return jsonify({"message": f"Token {token} TTL extended successfully"}), http.HTTPStatus.OK
    
    return jsonify({"error": "Token not found"}), http.HTTPStatus.NOT_FOUND

