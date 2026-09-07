# How the practice application works

Hydra is the OAuth2/OpenID Connect service. The small portal in this project supplies synthetic login and consent screens and a protected account page. Alice and Bob are demo subjects; their selection is not a production login system.

The gateway exposes a stable issuer at `http://localhost:8080`. Requests under `/oauth2/`, `/.well-known/`, and `/userinfo` reach the active Hydra deployment. Other requests reach the portal. The portal talks to Hydra's administrative API on the container network, so your browser never needs direct admin access.

A login starts an authorization-code flow with state and PKCE. The portal stores the tokens on the server and sets an HTTP-only session cookie. The protected page introspects the current access token on each request. Refreshing the session asks the active Hydra to redeem the original refresh token.

This makes migration behavior visible: preserving rows is useful only if the target Hydra can still interpret their relationships and cryptographic state. The issuer URL, system secret, cookies, client credentials, and data must agree across the transition.

The local Compose file starts MySQL and PostgreSQL, initializes their schemas with Hydra's own migrations, and starts only source Hydra. Target Hydra has a separate Compose profile, preventing it from creating application state while the destination is being prepared.

The local database ports bind to loopback: MySQL 13306 and PostgreSQL 15432. Source admin is 4445; target admin is 5445 when started. In AWS, database connections use the native private Aurora hostnames and verify TLS certificates. The HTTP practice portal is reached through an SSM tunnel.

**Predict before building:** if PostgreSQL has an empty Hydra schema and the target starts, will an existing MySQL refresh token work? Explain why neither an empty schema nor a healthy container proves a successful migration.

[Build the demo](build.md)
