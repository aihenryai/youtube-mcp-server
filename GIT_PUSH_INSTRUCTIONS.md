# 🚀 Git Push Instructions - YouTube MCP Server v2.0

## ✅ Pre-Push Checklist

בדוק את הדברים הבאים לפני Push:

### סודות (Critical!)
- [ ] אין .env עם API keys אמיתיים
- [ ] אין credentials.json
- [ ] אין token.json
- [ ] .gitignore מקיף (כולל .env, credentials.json, וכו')

### קבצים חדשים
- [ ] SECURITY.md קיים
- [ ] GOOGLE_CLOUD_DEPLOYMENT.md קיים
- [ ] DEPLOYMENT_PLAN.md קיים
- [ ] HANDOVER.md קיים
- [ ] utils/secret_manager.py קיים
- [ ] cloudbuild.yaml קיים
- [ ] Dockerfile עודכן
- [ ] README.md עודכן

## 🚀 Option 1: Using the Script (Recommended)

### Windows:
```cmd
# פשוט תריץ את הסקריפט:
git_commit.bat
```

הסקריפט יעשה:
1. ✅ בדיקת סטטוס
2. ✅ הוספת כל הקבצים החדשים
3. ✅ Commit עם הודעה מפורטת
4. ✅ Push ל-GitHub (אחרי אישור)

## 🔧 Option 2: Manual Commands

### בדיקה ראשונית:
```bash
cd "C:\Users\henry\claude files\youtube-mcp-server-local"

# בדוק סטטוס
git status

# בדוק שאין סודות
git status | findstr /i ".env credentials token"
```

### הוספת קבצים:
```bash
# תיעוד
git add SECURITY.md
git add GOOGLE_CLOUD_DEPLOYMENT.md
git add DEPLOYMENT_PLAN.md
git add HANDOVER.md

# פריסה
git add Dockerfile
git add .dockerignore
git add .gcloudignore
git add cloudbuild.yaml

# קוד
git add utils/secret_manager.py
git add .env.example
git add README.md
```

### Commit:
```bash
git commit -m "v2.0: Production-ready with Secret Manager and comprehensive security

- Add SECURITY.md with security policy
- Add GOOGLE_CLOUD_DEPLOYMENT.md with GCP guide
- Add Secret Manager integration
- Add deployment documentation
- Update Dockerfile with security hardening
- Update README with new features

Security improvements:
- CORS properly configured
- OAuth2 tokens encrypted
- Secret Manager support
- Non-root Docker user
- Health checks enabled"
```

### Push:
```bash
# Push ל-main branch
git push origin main

# אופציונלי: צור release tag
git tag -a v2.0 -m "Version 2.0 - Production Ready"
git push origin v2.0
```

## ⚠️ אם יש בעיות

### "Authentication failed":
```bash
# אם משתמש ב-GitHub token:
git remote set-url origin https://YOUR_TOKEN@github.com/aihenryai/youtube-mcp-server.git

# או השתמש ב-GitHub Desktop / Git Credential Manager
```

### "Nothing to commit":
```bash
# בדוק שהקבצים באמת לא tracked:
git status --untracked-files

# אם הם ignored בטעות:
git check-ignore -v SECURITY.md
```

### "Rejected - non-fast-forward":
```bash
# קח את השינויים האחרונים מ-GitHub:
git pull origin main --rebase

# ואז push שוב:
git push origin main
```

## 🎯 After Push

1. **בדוק ב-GitHub:**
   - https://github.com/aihenryai/youtube-mcp-server
   - וודא שכל הקבצים החדשים שם
   - בדוק ש-.env לא נמצא שם!

2. **צור Release (אופציונלי):**
   - לך ל-Releases
   - לחץ על "Create new release"
   - Tag: v2.0
   - Title: "Version 2.0 - Production Ready"
   - Description: העתק מ-HANDOVER.md

3. **עדכן README Badge (אופציונלי):**
   - הוסף badge של version
   - הוסף badge של build status

## 📊 Expected Results

אחרי Push מוצלח תראה:
- ✅ 10+ קבצים חדשים ב-GitHub
- ✅ README.md מעודכן
- ✅ Commit message מפורט
- ✅ אין .env או סודות
- ✅ כל התיעוד זמין

## 🔐 Security Verification

אחרי Push, בדוק ב-GitHub:
```bash
# חפש בכל הקבצים:
# 1. אין "AIzaSy..." (YouTube API key)
# 2. אין "credentials.json"
# 3. אין "token.json"
# 4. יש רק "test_api_key_for_testing" ב-.env.example
```

---

**Ready? Run:** `git_commit.bat`

**Questions?** See DEPLOYMENT_PLAN.md for full instructions.
