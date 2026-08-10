# Tom gateway

`tom_gateway.py` is Tom Assist's narrow Python sidecar for the pinned read-only
`tom_master` runtime. It serves HTTP-shaped JSON over a user-only Unix socket.

Preview purity is structural: preview calls only a local exact mirror of the
applicable structural trigger and RGM's `VectorStore.query`. Importing the
pinned `interface` package would also initialize unrelated chat/provider code,
so the 20-line upstream trigger wrapper is not imported.
The upstream `retrieve_ltm_with_stm_triggers` wrapper is intentionally not used
because the pinned implementation contains a mutating RGM read.

Create the isolated environment and install only the resolved runtime and test
imports:

```sh
python3 -m venv .venv-gateway
.venv-gateway/bin/python -m pip install -r gateway/requirements-dev.txt
```
