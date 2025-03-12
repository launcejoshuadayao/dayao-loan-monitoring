from werkzeug.security import generate_password_hash

password = "12345"  # Change this to the password you want
hashed_password = generate_password_hash(password, method="pbkdf2:sha256")

print("Hashed Password:", hashed_password)