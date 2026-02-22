# GCP Cloud SQL Stuck on Creation - Troubleshooting

## 🔴 Common Causes

### 1. **Billing Not Fully Propagated**
Even if you linked billing, it takes 2-5 minutes to propagate.

**Fix:**
```bash
# Check billing status
gcloud billing projects describe YOUR_PROJECT_ID

# If not linked, wait 2-3 minutes and retry
# Or create instance via console (faster)
```

### 2. **APIs Not Fully Enabled**
Cloud SQL needs multiple APIs enabled.

**Fix:**
```bash
# Enable ALL required APIs
gcloud services enable sqladmin.googleapis.com
gcloud services enable servicenetworking.googleapis.com
gcloud services enable compute.googleapis.com

# Wait 30 seconds
gcloud sql instances list
```

### 3. **Service Networking Issue**
Cloud SQL needs a private connection setup (can hang here).

**Fix - Create via Console (Recommended):**
```bash
# Open console directly
open "https://console.cloud.google.com/sql/instances/create?project=YOUR_PROJECT_ID"
```

### 4. **Quota Limits**
Free tier has limits on concurrent operations.

**Check:**
```bash
gcloud sql instances list
# If you see operations pending, wait for them to finish
```

---

## 🚀 QUICK FIX: Use Console Instead

**Console is faster and shows progress:**

```bash
open "https://console.cloud.google.com/sql/instances/create"
```

**Steps:**
1. Choose **PostgreSQL 15**
2. Instance ID: `znayka-db`
3. Password: Generate or set `znayka`
4. Region: `us-central1` (or your region)
5. Machine type: **db-f1-micro** (cheapest)
6. Storage: 10GB
7. Click **Create**

**Wait 3-5 minutes** (shows progress bar).

---

## 🔄 ALTERNATIVE: Skip Cloud SQL, Use Railway PostgreSQL

If GCP keeps hanging, use Railway PostgreSQL + GCP Cloud Run:

```bash
# 1. Create DB on Railway
railway add --database postgres

# 2. Get connection string
railway variables

# 3. Deploy to Cloud Run with Railway DB
export DB_URL="postgresql+asyncpg://..."

gcloud run deploy znayka \
  --image gcr.io/$PROJECT_ID/znayka \
  --set-env-vars="DATABASE_URL=$DB_URL"
```

---

## 🔍 DEBUG Commands

```bash
# Check if operation is stuck
gcloud sql operations list --instance=znayka-db

# Check logs
gcloud logging read "resource.type=cloudsql_database" --limit=20

# Cancel stuck operation (if pending > 10 min)
gcloud sql operations cancel OPERATION_ID
```

---

## ⚡ NUCLEAR OPTION: Reset Everything

```bash
# Delete project and start fresh
export PROJECT_ID="znayka-$(date +%s)"

gcloud projects create $PROJECT_ID
gcloud config set project $PROJECT_ID

# Wait 2 minutes for billing propagation
echo "Waiting for billing..."
sleep 120

# Create SQL via console (more reliable)
open "https://console.cloud.google.com/sql/instances/create?project=$PROJECT_ID"
```

---

## 💡 My Recommendation

**Use Railway PostgreSQL + GCP Cloud Run:**
- Railway DB: **Free** (PostgreSQL with pgvector)
- GCP Cloud Run: **Free tier** (2M requests)
- **No hanging, no billing issues**

**Want me to set this up?**
