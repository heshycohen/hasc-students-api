# Create a user and add your logo

## Create a user and log in

1. **Start the backend** (if it’s not already running):
   ```powershell
   cd \\hasc-aws-sql01\ACCESS\Rock-Access\rock-access-web\backend
   .\venv\Scripts\activate
   daphne config.asgi:application
   ```

2. **Create an admin/superuser** in a **new** terminal.

   **Option A — Create `hcohen@hasc.net` (recommended):**
   ```powershell
   cd \\hasc-aws-sql01\ACCESS\Rock-Access\rock-access-web\backend
   .\venv\Scripts\activate
   python manage.py create_hcohen_superuser
   ```
   This creates superuser **hcohen@hasc.net** with temporary password **ChangeMe123!** (change it after first login). To use a different password:
   ```powershell
   $env:HCOHEN_PASSWORD = "YourPreferredPassword"
   python manage.py create_hcohen_superuser
   ```

   **Option B — Create any other user (interactive):**
   ```powershell
   python manage.py createsuperuser
   ```
   Enter email address and password when prompted.

3. **Log in** in the browser:
   - Open **http://localhost:3000**
   - Use the same **email** and **password** you set for the superuser.

You can also log in at **http://localhost:8000/admin** with the same account.

---

## Add your logo

The login page shows a logo if the file is present. Your HASC “Experience the Magic” logo is in the Cursor project assets.

1. **Where to put the logo**
   - Put your logo file in the frontend **public** folder as **`logo.png`**:
   - **Destination folder:**  
     `\\hasc-aws-sql01\ACCESS\Rock-Access\rock-access-web\frontend\public\`
   - **Filename:** `logo.png` (or `logo.svg` — both work)

2. **How to “send” or add it**
   - **Your logo file** (from Cursor) is here:
     ```
     C:\Users\hcohen\.cursor\projects\hasc-aws-sql01-ACCESS-Rock-Access\assets\c__Users_hcohen_AppData_Roaming_Cursor_User_workspaceStorage_a7e7cca5372a47fd268a00d2d8ca329e_images_d2dcc940-b199-4ae6-af53-2f0ff89e809f-6e4b5bb0-c75e-4228-9d7a-5b90144cbfc2.png
     ```
   - **Option A — File Explorer:** Copy that file into  
     `\\hasc-aws-sql01\ACCESS\Rock-Access\rock-access-web\frontend\public\`  
     and **rename** it to **`logo.png`**.
   - **Option B — PowerShell (one command):**
     ```powershell
     Copy-Item "C:\Users\hcohen\.cursor\projects\hasc-aws-sql01-ACCESS-Rock-Access\assets\c__Users_hcohen_AppData_Roaming_Cursor_User_workspaceStorage_a7e7cca5372a47fd268a00d2d8ca329e_images_d2dcc940-b199-4ae6-af53-2f0ff89e809f-6e4b5bb0-c75e-4228-9d7a-5b90144cbfc2.png" "\\hasc-aws-sql01\ACCESS\Rock-Access\rock-access-web\frontend\public\logo.png" -Force
     ```
   - **If you use the local frontend** (`%LOCALAPPDATA%\RockAccessFrontend`): copy `logo.png` into that app’s **public** folder too, then refresh **http://localhost:3000**.

3. **Sizing**
   - The logo is limited to **80px height** and full width of the login box so it stays readable. Use a PNG or SVG that looks good at that size (e.g. 160–320px wide for PNG).

If no `logo.png` or `logo.svg` is in `public/`, the logo area is hidden and the rest of the page works as before.
