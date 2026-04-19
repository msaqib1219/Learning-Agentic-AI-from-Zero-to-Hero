# 🚀 Railway → SnapDeploy + Supabase: Quick Start Guide

**Status**: ✅ Zero Credit Card Required  
**Time**: ~1 hour  
**Difficulty**: Easy (copy-paste)

---

## ⚠️ Important: Credit Card Issue Resolved

**Problem You Encountered:**
- Railway trial ended
- Render free tier asks for credit card (even though it's free)
- Fly.io free trial only (2 hours then CC required)

**Solution:**
Use **SnapDeploy** (free forever, no CC) + **Supabase** (free forever, no CC)

---

## Architecture: CC-Free Stack

```
Netlify (no CC) ← Frontend
        ↓ API calls
SnapDeploy (no CC) ← Backend
        ↓ SQL queries
Supabase (no CC) ← Database
```

---

## Phase 1: Supabase PostgreSQL (FREE, NO CC)

1. Go to [supabase.com](https://supabase.com) → **Sign Up**
   - Email + password (no CC screen!)
2. Click **New Project**
   - Name: `agentic-ai`
   - Password: Generate strong password
   - Region: Choose closest
   - Plan: **Free**
3. Wait 1-3 minutes for provisioning
4. Go to **Project Settings** → **Database**
5. Copy **Connection String** (URI):
   ```
   postgresql://postgres:YourPassword@db.xxxxx.supabase.co:5432/postgres
   ```
   Save as `DATABASE_URL`

✅ **Cost**: FREE  
✅ **Credit Card**: NO

---

## Phase 2: SnapDeploy FastAPI Backend (FREE, NO CC)

1. Go to [snapdeploy.dev](https://snapdeploy.dev) → **Sign Up**
   - Email + password (no CC screen!)
2. # Wrong instructions 
   Install CLI:
   ```bash
   npm install -g snapdeploy
   # or: brew install snapdeploy
   # or: pip install snapdeploy
   ```
3. In your project root, create `snapdeploy.json`:
   ```json
   {
     "runtime": "python:3.11",
     "buildCommand": "pip install -r backend/requirements.txt",
     "startCommand": "cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT"
   }
   ```
4. Commit to git:
   ```bash
   git add snapdeploy.json
   git commit -m "add snapdeploy config"
   ```
5. Deploy:
   ```bash
   snapdeploy deploy
   ```
6. Follow CLI prompts (select repo/branch)
7. Get your URL: `https://your-app.snapdeploy.app`

✅ **Cost**: FREE  
✅ **Credit Card**: NO  
✅ **Cold start**: 10-30 sec (acceptable)

---

## Phase 3: Set Environment Variables in SnapDeploy

```bash
snapdeploy env set DATABASE_URL="postgresql://postgres:password@db.xxxxx.supabase.co:5432/postgres"
snapdeploy env set GEMINI_API_KEY="your_gemini_key"
snapdeploy env set QDRANT_URL="your_qdrant_url"
snapdeploy env set QDRANT_API_KEY="your_qdrant_key"
snapdeploy env set FRONTEND_URL="https://your-netlify-site.netlify.app"
snapdeploy env set ALLOWED_ORIGINS="https://your-netlify-site.netlify.app,http://localhost:3000"
snapdeploy env set JWT_SECRET="your_jwt_secret"
```

Trigger redeploy:
```bash
snapdeploy deploy
```

---

## Phase 4: Initialize Supabase Schema

In Supabase dashboard:
1. Go to **SQL Editor**
2. Run initialization SQL from your `backend/database.py`
3. Verify tables created

---

## Phase 5: Update Netlify Frontend

1. Go to [app.netlify.com](https://app.netlify.com)
2. Select your site → **Site Settings** → **Build & deploy** → **Environment**
3. Update `REACT_APP_API_URL`:
   ```
   https://your-app.snapdeploy.app
   ```
4. Click **Trigger deploy**

---

## Phase 6: Test Everything

1. Open frontend URL
2. **Test OAuth2**: Sign in (Google, GitHub, etc.)
3. **Test Chat**: Send a message
4. **Test Profile**: View user data
5. **Check Console**: No CORS errors?

---

## ✅ Success Indicators

- [ ] SnapDeploy shows "Deployed" status
- [ ] Supabase project shows "Active"
- [ ] `curl https://your-app.snapdeploy.app/api/health` → `{"status": "healthy"}`
- [ ] Frontend signs in successfully
- [ ] Chat endpoint returns responses
- [ ] No CORS errors in browser console

---

## 🎯 Zero Credit Card Checklist

- [x] Supabase: FREE 500MB PostgreSQL, no CC required
- [x] SnapDeploy: FREE forever, no CC required
- [x] Netlify: FREE frontend, no CC required
- [x] Gemini API: Already have key, no changes
- [x] Qdrant Cloud: Already have account, no changes

**TOTAL**: 0 credit cards needed ✓

---

## 📚 Documentation

For more details, see:
- `specs/railway-to-render-migration/CREDIT_CARD_FREE_OPTION.md` — Full breakdown
- `specs/railway-to-render-migration/DEPLOYMENT_GUIDE.md` — Original detailed guide (adapt SnapDeploy steps)
- `specs/railway-to-render-migration/QUICK_REFERENCE.md` — Cheat sheet

---

## 🆘 Troubleshooting

### "SnapDeploy asks for credit card"
- This should not happen. Contact support@snapdeploy.dev
- Alternative: Use their GitHub-based deployment (no signup needed)

### "Database connection refused"
- Verify `DATABASE_URL` format
- Check Supabase project is "Active" (not paused)
- Try: `psql $DATABASE_URL` locally

### "CORS error in browser"
- Verify `ALLOWED_ORIGINS` env var includes your Netlify domain
- Verify `FRONTEND_URL` is set correctly
- Redeploy SnapDeploy: `snapdeploy deploy`

### "Cold start too slow"
- SnapDeploy: 10-30 sec is normal (free tier)
- Acceptable for MVP; upgrade later if needed

---

## Cost Summary

| Service | Cost | CC Needed? |
|---------|------|-----------|
| Supabase PostgreSQL | FREE | ✓ NO |
| SnapDeploy Backend | FREE | ✓ NO |
| Netlify Frontend | FREE | ✓ NO |
| Gemini API | (existing) | ✓ NO |
| Qdrant Cloud | (existing) | ✓ NO |
| **TOTAL** | **$0/month** | **✓ NO** |

---

## Ready? Start Here

1. Create Supabase account (2 min)
2. Install snapdeploy CLI (1 min)
3. Deploy to SnapDeploy (5 min)
4. Set env vars (2 min)
5. Update Netlify (3 min)
6. Test integration (5 min)

**Total: ~20 minutes + waiting time** ✓

🎉 **No credit card required at any step!**
