# 🚀 EasyPanel Final Steps — Domains + SSL + Testing

> Frontend build is in progress. Once complete (~15 min), follow these steps to finalize production deployment.

---

## 📊 Current Status

| Component | Status | Build Time |
|-----------|--------|-----------|
| Backend App | ✅ Built & Running | ~5-8 min |
| Frontend App | 🔄 Building in progress | ~10-15 min |
| Domains | ⏳ Pending | 2 min |
| SSL Certificates | ⏳ Pending | Auto (Let's Encrypt) |

---

## ⏱️ STEP 1: Wait for Frontend Build Completion

**Timeline:** ~10-15 minutes from when build started

Monitor in EasyPanel:
1. **Dashboard** → `fiscalai-frontend` app
2. **Logs** section — watch for:
   ```
   ✅ Build completed successfully
   ✅ Image built and pushed
   ✅ Container started
   ✅ App is running on http://localhost:80
   ```

**What's happening in the build:**
- Stage 1: Node:20-alpine installs npm dependencies
- Stage 2: Vite compiles React TypeScript code → optimized dist/
- Stage 3: Nginx container receives dist/ files and starts serving on port 80

If build fails:
- Check **Build Logs** for error message
- Common issues:
  - `npm ERR!` — missing package (check package.json syntax)
  - `tsc error` — TypeScript compilation error in src/
  - `vite build error` — check vite.config.ts
- See `EASYPANEL_TROUBLESHOOT.md` for detailed troubleshooting

---

## ✅ STEP 2: Configure Backend Domain + SSL

Once **both backend and frontend apps are running** (both show green "Running" status):

### 2.1 Add Backend Domain

1. **EasyPanel Dashboard** → `fiscalai-backend` app
2. **Domains** section → **+ Add Domain**
3. Fill in:
   ```
   Domain: fiscalai-backend.6hjchk.easypanel.host
   SSL: ☑️ Let's Encrypt (automatic)
   ```
4. **Save** (Let's Encrypt will auto-generate certificate)

⏱️ **Time:** ~30 seconds to generate SSL cert

---

## ✅ STEP 3: Configure Frontend Domain + SSL

1. **EasyPanel Dashboard** → `fiscalai-frontend` app
2. **Domains** section → **+ Add Domain**
3. Fill in:
   ```
   Domain: fiscalai.6hjchk.easypanel.host
   SSL: ☑️ Let's Encrypt (automatic)
   ```
4. **Save**

⏱️ **Time:** ~30 seconds

---

## ✅ STEP 4: Verify Backend Health

After domain setup, test backend connectivity:

```powershell
curl -k https://fiscalai-backend.6hjchk.easypanel.host/health
```

Expected response:
```json
{"status":"healthy","service":"FiscalAI API"}
```

**If request fails:**
- Wait 30 seconds for SSL cert generation
- Check EasyPanel Logs for errors
- Verify domain name has no typos

---

## ✅ STEP 5: Verify Frontend Health

Test frontend nginx:

```powershell
curl -k https://fiscalai.6hjchk.easypanel.host/health
```

Expected response:
```json
{"status":"healthy","service":"FiscalAI Frontend"}
```

---

## ✅ STEP 6: Browser Test — Frontend Access

Open browser and navigate to:
```
https://fiscalai.6hjchk.easypanel.host
```

### Expected behavior:

1. ✅ Page loads (no CORS errors)
2. ✅ Login form appears with:
   - Email input field
   - Password input field
   - Login button
   - No console errors (check F12 → Console)
3. ✅ TLS/SSL padlock shows (green lock icon)

### If page doesn't load:

**Check Console (F12):**
- `CORS error` → Backend domain in VITE_API_BASE_URL is wrong
- `404` on /index.html → nginx routing issue (check nginx.conf)
- `Connection refused` → Backend not responding (verify backend domain works)

---

## ✅ STEP 7: End-to-End Login Test (Optional)

### Test Login Flow:

1. **Navigate to:** `https://fiscalai.6hjchk.easypanel.host`
2. **Open DevTools** (F12 → Network tab)
3. **Enter test credentials:**
   - Email: `test@example.com`
   - Password: `test_password_123`
4. **Click Login**
5. **Verify in Network tab:**
   - Request: `POST /api/v1/auth/login` to backend
   - Status: `200` (success) or `401` (invalid credentials)
   - Response body contains: `access_token`, `refresh_token`, `expires_in`

### Success = Dashboard loads:
```
GET /api/v1/documents → returns list of documents
```

### Failure = Stays on login:
- Check backend `/api/v1/auth/login` endpoint responding
- Verify DATABASE_URL in backend env vars points to correct PostgreSQL
- Check backend logs for auth errors

---

## 📋 Final Verification Checklist

- [ ] Backend build completed (green "Running" status)
- [ ] Frontend build completed (green "Running" status)
- [ ] Backend domain added: `fiscalai-backend.6hjchk.easypanel.host`
- [ ] Frontend domain added: `fiscalai.6hjchk.easypanel.host`
- [ ] Both SSL certificates active (Let's Encrypt)
- [ ] `curl` health check backend responds with `{"status":"healthy",...}`
- [ ] `curl` health check frontend responds with `{"status":"healthy",...}`
- [ ] Browser opens `https://fiscalai.6hjchk.easypanel.host` without errors
- [ ] Login form renders correctly
- [ ] Login attempt returns 200 or 401 (not connection error)
- [ ] Dashboard loads with document list (if login successful)

---

## 🎯 Success Criteria

**🟢 You are done when:**
1. Both services responding on production domains
2. Frontend login form accessible and functional
3. API endpoints responding with correct auth behavior
4. SSL/TLS certificates active on both domains

**URLs:**
```
Frontend:        https://fiscalai.6hjchk.easypanel.host
Backend API:     https://fiscalai-backend.6hjchk.easypanel.host
Backend Docs:    https://fiscalai-backend.6hjchk.easypanel.host/docs
Backend Health:  https://fiscalai-backend.6hjchk.easypanel.host/health
Frontend Health: https://fiscalai.6hjchk.easypanel.host/health
```

---

## 🆘 Troubleshooting

### Frontend shows blank page
1. Check browser console (F12) for errors
2. Verify VITE_API_BASE_URL env var:
   ```
   https://fiscalai-backend.6hjchk.easypanel.host/api
   ```
3. Check nginx.conf includes `try_files $uri $uri/ /index.html` for SPA routing

### Cannot connect to backend
1. Verify backend app is running (green status)
2. Test health endpoint: `curl https://fiscalai-backend.6hjchk.easypanel.host/health`
3. Check backend logs for errors

### SSL certificate not generating
1. Verify domain name has no typos
2. Wait 60 seconds (Let's Encrypt validation takes time)
3. Check EasyPanel app logs for SSL errors

### Login fails with 401
1. Verify user exists in database (test@example.com)
2. Check backend DATABASE_URL points to correct PostgreSQL
3. Check backend logs for auth validation errors

### CORS errors in browser console
1. Check backend app has `CORS_ORIGINS` environment variable
2. For production: `CORS_ORIGINS=["https://fiscalai.6hjchk.easypanel.host"]`
3. Restart backend app after changing env vars

---

## 📚 Additional Resources

- **EasyPanel Fix Guide:** `EASYPANEL_FIX_BUILD_ERROR.md`
- **Full Setup Checklist:** `EASYPANEL_CHECKLIST.md`
- **Troubleshooting Deep Dive:** `EASYPANEL_TROUBLESHOOT.md`
- **Docker Local Testing:** `DOCKER_SETUP.md`
- **Environment Variables:** `ENV_STRATEGY.md`

---

## ⏱️ Timeline Recap

| Phase | Duration | Status |
|-------|----------|--------|
| Backend build | 5-8 min | ✅ Complete |
| Frontend build | 10-15 min | 🔄 In Progress |
| Domain setup | 2 min | ⏳ Pending |
| SSL generation | 1 min | ⏳ Pending |
| Testing | 5-10 min | ⏳ Pending |
| **TOTAL** | **~30-40 min** | 🚀 Almost Ready |

---

## 🎉 Next Steps After This Completes

Once everything is verified:

1. ✅ Document the production URLs in your team
2. ✅ Share frontend URL: `https://fiscalai.6hjchk.easypanel.host`
3. ✅ Share API docs: `https://fiscalai-backend.6hjchk.easypanel.host/docs`
4. ✅ Begin user acceptance testing (UAT)
5. ✅ Monitor error logs in EasyPanel Dashboard → Logs section

---

## 💡 Important Notes

- **SSL Certificates:** Let's Encrypt auto-renews every 90 days (EasyPanel handles automatically)
- **Backup:** EasyPanel stores persistent data in volumes — no manual backup needed for MVP
- **Scaling:** If you need more resources, EasyPanel allows container resource configuration in App Settings
- **Custom Domain:** To use `fiscalai.your-domain.com`, update DNS CNAME to EasyPanel's load balancer

**FiscalAI is ready for production! 🚀**
