from nacl.signing import SigningKey
import os

print("Generating federated node keys...")

# generate keys
signing_key = SigningKey.generate()
verify_key = signing_key.verify_key

# ensure files save in current folder
base_path = os.path.dirname(__file__)

private_path = os.path.join(base_path, "fednet_private_key.pem")
public_path = os.path.join(base_path, "fednet_public_key.pem")

# write keys
with open(private_path, "wb") as f:
    f.write(signing_key.encode())

with open(public_path, "wb") as f:
    f.write(verify_key.encode())

print("✅ Keys created:")
print(private_path)
print(public_path)