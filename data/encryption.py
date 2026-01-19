import os
from cryptography.fernet import Fernet
from tqdm import tqdm

def get_key():
    # Generate a key
    key = Fernet.generate_key()

    # Create a Fernet object using the key
    fernet = Fernet(key)

    return key, fernet

def encrypt(fernet,paths:list):

    for folder_data in paths:
        print(os)

        for file in os.listdir(folder_data):
        
            file_path = os.path.join(folder_data,file)
                    
            # Open the files to be encrypted in binary read mode
            with open(file_path, 'rb') as f:
                original = f.read()

                # Encrypt the files content
                encrypted = fernet.encrypt(original)

                # Save the encrypted data
                os.makedirs('data/encrypted_data', exist_ok=True)
                with open(f'data/encrypted_data/{file}', 'wb') as f:
                    f.write(encrypted)
    return True

def save_key(key):
    # Load existing .env and save the key
    with open(".env", "r") as f:
        lines = f.readlines()
        # insert secret at the end of existing doc
        lines.insert(len(lines),f"\n\nsecret_key = '{key.decode()}'")

    # Write back to file
    with open(".env", "w") as f:
        f.writelines(lines)

    return True

# def decrypt_files(file, key):
#     with open(".env", "w") as f:
#         f.readlines()
#         for l in f:
#             if l.startswith("secret_key"):
#                 key=f.split("=")[1]
#     return 


if __name__ == "__main__":
    key, fernet = get_key()
    encrypt(fernet,paths=["data/CV_competences","data/research_paper"])
    save_key(key)