# Render deployment

Unzip and upload the **contents** to your repository root. Configure `APP_USER`, `APP_PASSWORD`, and `DATABASE_URL` on Render; use your existing PostgreSQL Internal Database URL. `render.yaml` uses Docker. The database schema is created automatically at startup. The app fails to start when `DATABASE_URL` is absent in deployment mode. Details in `LOGIN-RENDER-BN.txt`.
