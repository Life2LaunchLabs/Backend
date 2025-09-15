# Railway WebSocket Configuration

Based on debug logs, Railway is bypassing ASGI and routing WebSocket requests to Django HTTP.

## Required Railway Environment Variables

Add these in Railway dashboard:

```
RAILWAY_ASGI_ENABLE=true
RAILWAY_WEBSOCKET_ENABLE=true
ASGI_APPLICATION=mysite.asgi:application
WEBSOCKET_TIMEOUT=300
```

## Alternative: Railway Service Configuration

If environment variables don't work, try adding to railway.toml:

```toml
[build]
builder = "nixpacks"

[deploy]
healthcheckPath = "/api/health/"
healthcheckTimeout = 100
restartPolicyType = "never"

[experimental]
websockets = true

[deployment]
webSocketUpgradeMode = "auto"
asgiEnabled = true
```

## Debug Evidence

Request headers show Railway is intercepting WebSocket upgrades:
- X-Railway-Edge: railway/us-west2
- X-Railway-Request-Id: p8ibXX7YSNuIZQNJn6XIxQ

But routing to HTTP instead of ASGI WebSocket consumer.