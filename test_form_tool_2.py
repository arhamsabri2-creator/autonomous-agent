from form_tool_2 import fill_test_login

print("Test 1 - correct credentials (should show success message):")
print(fill_test_login("tomsmith | SuperSecretPassword!"))

print("\n\nTest 2 - wrong credentials (should show error message):")
print(fill_test_login("wronguser | wrongpass"))