# import os
# import pytest
# import tempfile
# import shutil
# from pathlib import Path
# from cryptography.fernet import Fernet
# import sys



# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# from data.encryption import get_key, encrypt, save_key
# from cryptography.fernet import Fernet



# # ============================================================================
# # UNIT TESTS
# # ============================================================================

# class TestGetKey:
#     """Unit tests for get_key function"""
    
#     def test_get_key_returns_tuple(self):
#         """Test that get_key returns a tuple"""
#         result = get_key()
#         assert isinstance(result, tuple)
#         assert len(result) == 2
    
#     def test_get_key_returns_valid_key(self):
#         """Test that get_key returns valid Fernet key"""
#         key, fernet = get_key()
#         assert isinstance(key, bytes)
#         assert isinstance(fernet, Fernet)
    
#     def test_key_can_encrypt_decrypt(self):
#         """Test that generated key can encrypt and decrypt"""
#         key, fernet = get_key()
#         message = b"Test message"
#         encrypted = fernet.encrypt(message)
#         decrypted = fernet.decrypt(encrypted)
#         assert decrypted == message
    
#     def test_keys_are_unique(self):
#         """Test that each call generates a unique key"""
#         key1, _ = get_key()
#         key2, _ = get_key()
#         assert key1 != key2



# class TestSaveKey:
#     """Unit tests for save_key function"""
    
#     @pytest.fixture
#     def temp_env_file(self):
#         """Create temporary .env file"""
#         fd, path = tempfile.mkstemp(suffix=".env")
#         os.close(fd)
#         yield path
#         if os.path.exists(path):
#             os.remove(path)
    
#     def test_save_key_creates_file(self, temp_env_file):
#         """Test that save_key creates .env file"""
#         os.remove(temp_env_file)  # Remove to test creation
#         key, _ = get_key()
#         result = save_key(key, temp_env_file)
#         assert result is True
#         assert os.path.exists(temp_env_file)
    
#     def test_save_key_appends_to_existing(self, temp_env_file):
#         """Test that save_key appends to existing file"""
#         # Write initial content
#         with open(temp_env_file, "w") as f:
#             f.write("EXISTING_VAR=value\n")
        
#         key, _ = get_key()
#         save_key(key, temp_env_file)
        
#         with open(temp_env_file, "r") as f:
#             content = f.read()
        
#         assert "EXISTING_VAR=value" in content
#         assert "SECRET_KEY=" in content
    
#     def test_saved_key_format(self, temp_env_file):
#         """Test that saved key has correct format"""
#         key, _ = get_key()
#         save_key(key, temp_env_file)
        
#         with open(temp_env_file, "r") as f:
#             content = f.read()
        
#         assert f"SECRET_KEY='{key.decode()}'" in content


# class TestDecrypt:
#     """Unit tests for decrypt function"""
    
#     @pytest.fixture
#     def encrypted_file(self):
#         """Create temporary encrypted file"""
#         key, fernet = get_key()
#         fd, path = tempfile.mkstemp()
        
#         content = b"Test content to encrypt"
#         encrypted = fernet.encrypt(content)
        
#         with os.fdopen(fd, 'wb') as f:
#             f.write(encrypted)
        
#         yield path, fernet, content
        
#         if os.path.exists(path):
#             os.remove(path)
    
#     # def test_decrypt_success(self, encrypted_file):
#     #     """Test successful decryption"""
#     #     encrypted_path, fernet, original_content = encrypted_file
        
#     #     with tempfile.NamedTemporaryFile(delete=False) as output:
#     #         output_path = output.name
        
#     #     try:
#     #         result = decrypt(fernet, encrypted_path, output_path)
#     #         assert result is True
            
#     #         with open(output_path, 'rb') as f:
#     #             decrypted = f.read()
            
#     #         assert decrypted == original_content
#     #     finally:
#     #         if os.path.exists(output_path):
#     #             os.remove(output_path)
    
#     def test_decrypt_wrong_key(self, encrypted_file):
#         """Test decryption with wrong key fails"""
#         encrypted_path, _, _ = encrypted_file
#         _, wrong_fernet = get_key()  # Different key
        
#         with tempfile.NamedTemporaryFile(delete=False) as output:
#             output_path = output.name
        
#         try:
#             result = decrypt(wrong_fernet, encrypted_path, output_path)
#             assert result is False
#         finally:
#             if os.path.exists(output_path):
#                 os.remove(output_path)


# # ============================================================================
# # INTEGRATION TESTS
# # ============================================================================

# class TestEncryptionWorkflow:
#     """Integration tests for complete encryption workflow"""
    
#     @pytest.fixture
#     def test_environment(self):
#         """Create complete test environment"""
#         # Create temporary directories
#         source_dir = tempfile.mkdtemp()
#         output_dir = tempfile.mkdtemp()
#         env_file = tempfile.NamedTemporaryFile(delete=False, suffix=".env")
#         env_file.close()
        
#         # Create test files
#         Path(source_dir, "test1.txt").write_text("Content 1")
#         Path(source_dir, "test2.csv").write_text("a,b,c\n1,2,3")
        
#         subdir = Path(source_dir, "subdir")
#         subdir.mkdir()
#         Path(subdir, "test3.json").write_text('{"key": "value"}')
        
#         yield source_dir, output_dir, env_file.name
        
#         # Cleanup
#         shutil.rmtree(source_dir, ignore_errors=True)
#         shutil.rmtree(output_dir, ignore_errors=True)
#         if os.path.exists(env_file.name):
#             os.remove(env_file.name)
    
#     def test_full_encryption_workflow(self, test_environment):
#         """Test complete encryption workflow"""
#         source_dir, output_dir, env_file = test_environment
        
#         # Generate key
#         key, fernet = get_key()
        
#         # Encrypt files
#         result = encrypt(fernet, source_dir, output_dir)
#         assert result is True
        
#         # Verify encrypted files exist
#         encrypted_files = get_all_files(output_dir)
#         assert len(encrypted_files) == 3
        
#         # Save key
#         result = save_key(key, env_file)
#         assert result is True
        
#         # Verify key was saved
#         with open(env_file, "r") as f:
#             content = f.read()
#         assert "SECRET_KEY=" in content
    
#     def test_encrypt_decrypt_roundtrip(self, test_environment):
#         """Test that files can be encrypted and then decrypted"""
#         source_dir, output_dir, _ = test_environment
        
#         # Generate key
#         key, fernet = get_key()
        
#         # Encrypt
#         encrypt(fernet, source_dir, output_dir)
        
#         # Decrypt one file
#         encrypted_file = os.path.join(output_dir, "test1.txt")
#         decrypted_dir = tempfile.mkdtemp()
#         decrypted_file = os.path.join(decrypted_dir, "test1.txt")
        
#         try:
#             decrypt(fernet, encrypted_file, decrypted_file)
            
#             # Verify content matches original
#             with open(decrypted_file, 'r') as f:
#                 content = f.read()
#             assert content == "Content 1"
#         finally:
#             shutil.rmtree(decrypted_dir, ignore_errors=True)
    
#     def test_preserves_directory_structure(self, test_environment):
#         """Test that directory structure is preserved"""
#         source_dir, output_dir, _ = test_environment
        
#         key, fernet = get_key()
#         encrypt(fernet, source_dir, output_dir)
        
#         # Check that subdirectory exists
#         encrypted_subdir_file = os.path.join(output_dir, "subdir", "test3.json")
#         assert os.path.exists(encrypted_subdir_file)
    
#     def test_empty_directory_handling(self):
#         """Test handling of empty directory"""
#         with tempfile.TemporaryDirectory() as source_dir:
#             with tempfile.TemporaryDirectory() as output_dir:
#                 key, fernet = get_key()
#                 result = encrypt(fernet, source_dir, output_dir)
#                 assert result is False


# # ============================================================================
# # PARAMETRIZED TESTS
# # ============================================================================

# class TestEncryptionWithDifferentFileTypes:
#     """Test encryption with various file types"""
    
#     @pytest.mark.parametrize("filename,content", [
#         ("test.txt", b"Plain text content"),
#         ("test.json", b'{"key": "value"}'),
#         ("test.csv", b"a,b,c\n1,2,3"),
#         ("test.bin", bytes(range(256))),
#         ("test.pdf", b"%PDF-1.4\n%\xe2\xe3\xcf\xd3"),
#     ])
#     def test_encrypt_different_file_types(self, filename, content):
#         """Test encryption of different file types"""
#         with tempfile.TemporaryDirectory() as source_dir:
#             with tempfile.TemporaryDirectory() as output_dir:
#                 # Create test file
#                 file_path = Path(source_dir, filename)
#                 file_path.write_bytes(content)
                
#                 # Encrypt
#                 key, fernet = get_key()
#                 result = encrypt(fernet, source_dir, output_dir)
#                 assert result is True
                
#                 # Verify encrypted file exists
#                 encrypted_path = Path(output_dir, filename)
#                 assert encrypted_path.exists()
                
#                 # Verify content is different (encrypted)
#                 encrypted_content = encrypted_path.read_bytes()
#                 assert encrypted_content != content


# if __name__ == "__main__":
#     pytest.main([__file__, "-v", "--tb=short"])