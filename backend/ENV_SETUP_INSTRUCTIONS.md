# .env File Setup Instructions

## File Location
The `.env` file should be located at:
```
rock-access-web/backend/.env
```

## Required Content

Copy and paste this exact content into your `.env` file:

```env
# KMS Provider - Set to Azure for envelope encryption
KMS_PROVIDER=azure

# Azure Key Vault Configuration
AZURE_KEY_VAULT_URL=https://rock-access-vault-hcohen.vault.azure.net/
AZURE_KEY_NAME=yencryption-ke
AZURE_TENANT_ID=0e25f169-d12b-495a-944a-8c6c278d065e
AZURE_CLIENT_ID=655900a3-da6c-47d2-850d-67503411b782
AZURE_CLIENT_SECRET=<SET_IN_AZURE_APP_SERVICE_SETTINGS>

# Envelope Encryption Settings (optional - defaults to 4096 bytes)
ENVELOPE_ENCRYPTION_THRESHOLD=4096
```

## Manual Verification Steps

1. **Navigate to the backend folder:**
   - Open File Explorer
   - Go to: `\\hasc-aws-sql01\ACCESS\Rock-Access\rock-access-web\backend\`

2. **Check if .env file exists:**
   - The file might be hidden (starts with a dot)
   - In File Explorer, go to View → Show → Hidden items
   - Look for a file named `.env`

3. **If the file doesn't exist, create it:**
   - Right-click in the folder → New → Text Document
   - Name it `.env` (make sure it's `.env` not `.env.txt`)
   - If Windows adds `.txt`, rename it to remove the extension
   - Open it with Notepad
   - Paste the content above
   - Save and close

4. **Verify the file content:**
   - Open the `.env` file
   - Make sure all 7 lines are present:
     - KMS_PROVIDER=azure
     - AZURE_KEY_VAULT_URL=https://rock-access-vault-hcohen.vault.azure.net/
     - AZURE_KEY_NAME=yencryption-ke
     - AZURE_TENANT_ID=0e25f169-d12b-495a-944a-8c6c278d065e
     - AZURE_CLIENT_ID=655900a3-da6c-47d2-850d-67503411b782
     - AZURE_CLIENT_SECRET=<SET_IN_AZURE_APP_SERVICE_SETTINGS>
     - ENVELOPE_ENCRYPTION_THRESHOLD=4096

## Important Notes

- The `.env` file is already in `.gitignore`, so it won't be committed to Git
- Never share the contents of this file publicly
- Keep the Client Secret secure
- If you need to change any values, edit this file directly

## Next Steps

Once the `.env` file is created and verified:

1. Install packages: `pip install -r requirements.txt`
2. Wait 5-10 minutes for RBAC permissions to propagate
3. Test the connection using the test script
