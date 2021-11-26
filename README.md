My personal blog

[![builds.sr.ht status](https://builds.sr.ht/~jwaterhouse/blog.svg)](https://builds.sr.ht/~jwaterhouse/blog?)

# Development environment

```bash
# Create virtual environment
python -m venv .venv

# Activate the virtual env
. .venv/bin/activate

# Install the package dependencies
python -m pip install -r requirements.txt

# Generate some local certificates for testing (required by gemini)
openssl req -x509 -out localhost.crt -keyout localhost.key \
    -newkey rsa:2048 -nodes -sha256 \
    -subj '/CN=localhost' -extensions EXT -config <( \
    printf "[dn]\nCN=localhost\n[req]\ndistinguished_name = dn\n[EXT]\nsubjectAltName=DNS:localhost\nkeyUsage=digitalSignature\nextendedKeyUsage=serverAuth")

# Run the server
python blog/app.py --crt_file localhost.crt --key_file localhost.key
```
