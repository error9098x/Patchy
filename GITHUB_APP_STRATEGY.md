# GitHub App Strategy: Development vs Production

**Date**: 2026-04-23 22:38  
**Question**: Should we use "Any account" now or later?

---

## TL;DR

✅ **Now**: Create dev app with "Only on this account"  
✅ **Later**: Create production app with "Any account"  
✅ **Strategy**: Two separate apps for safety

---

## The Two-App Strategy

### App 1: Development (Create Now)

**Settings**:
- Name: `Patchy-Dev` or `Patchy-YourUsername`
- Installation: **"Only on this account"**
- Webhook: ngrok URL (http://abc123.ngrok.io/webhook)
- Homepage: http://localhost:5001

**Purpose**:
- Testing and development
- Debug on your repos only
- Break things safely
- Learn and iterate

**Timeline**: Use for 2-4 weeks while building

---

### App 2: Production (Create Later)

**Settings**:
- Name: `Patchy` (official)
- Installation: **"Any account"** ✅
- Webhook: https://patchy.app/webhook
- Homepage: https://patchy.app

**Purpose**:
- Public use by anyone
- Stable and monitored
- Professional deployment
- Real users

**Timeline**: Create when ready to launch publicly

---

## Why Not "Any Account" Now?

### Technical Reasons

1. **Unstable Webhook**
   - ngrok URL changes every restart
   - Users would get broken webhooks
   - Bad user experience

2. **Local Development**
   - Running on localhost:5001
   - Not accessible to other users
   - Can't handle real traffic

3. **No Error Handling**
   - Code is still being built
   - Bugs will happen
   - Would affect other users' repos

4. **No Monitoring**
   - Can't track issues
   - Can't debug user problems
   - No logging infrastructure

### Safety Reasons

1. **Blast Radius**
   - Mistake only affects your repos
   - No risk to other users
   - Easy to fix and retry

2. **Testing Freedom**
   - Can test destructive operations
   - Can experiment with permissions
   - Can break things without consequences

3. **Privacy**
   - Your code stays on your machine
   - No user data to protect yet
   - No compliance requirements

---

## When to Switch to "Any Account"

### Prerequisites Checklist

**Infrastructure**:
- [ ] Deployed to Railway/Vercel
- [ ] Custom domain configured (patchy.app)
- [ ] Webhook endpoint is stable
- [ ] SSL certificate active
- [ ] Uptime monitoring in place

**Code Quality**:
- [ ] All features tested thoroughly
- [ ] Error handling implemented
- [ ] Rate limiting in place
- [ ] Logging and monitoring active
- [ ] Security review complete

**Legal/Compliance**:
- [ ] Privacy policy written
- [ ] Terms of service ready
- [ ] Data handling documented
- [ ] GDPR compliance (if EU users)

**User Experience**:
- [ ] Documentation complete
- [ ] Support channel ready (email/Discord)
- [ ] Onboarding flow tested
- [ ] Error messages are helpful

---

## Migration Timeline

### Week 1-2: Development App
```
✅ Create dev app ("Only on this account")
✅ Build features locally
✅ Test on your repos
✅ Use ngrok for webhooks
```

### Week 3-4: Staging
```
✅ Deploy to Railway
✅ Still use dev app
✅ Test with stable URL
✅ Fix bugs
```

### Week 5: Production Prep
```
✅ Create production app ("Any account")
✅ Update production .env
✅ Test production app on test repo
✅ Verify everything works
```

### Week 6+: Public Launch
```
✅ Switch to production app
✅ Announce to users
✅ Monitor closely
✅ Keep dev app for testing new features
```

---

## How to Create Production App (Later)

### Step 1: Keep Dev App
- Don't delete or modify dev app
- You'll still use it for testing

### Step 2: Create New App
Go to: https://github.com/settings/apps/new

Fill in:
- **Name**: `Patchy` (official name)
- **Homepage**: `https://patchy.app`
- **Webhook**: `https://patchy.app/webhook`
- **Installation**: **"Any account"** ✅
- **Same permissions** as dev app

### Step 3: Get New Credentials
- New App ID
- New Client ID/Secret
- New Private Key
- New Webhook Secret

### Step 4: Update Production .env
```bash
# .env.production
GITHUB_APP_ID=<new_production_app_id>
GITHUB_CLIENT_ID=<new_production_client_id>
GITHUB_CLIENT_SECRET=<new_production_secret>
# ... etc
```

### Step 5: Deploy
```bash
# Railway deployment
railway up
railway env set GITHUB_APP_ID=<production_app_id>
# ... set all production env vars
```

### Step 6: Test
- Install production app on test repo
- Trigger scan
- Verify PR creation
- Check webhook delivery

### Step 7: Launch
- Announce on Twitter/Reddit
- Add to GitHub Marketplace
- Monitor for issues

---

## Benefits of Two-App Strategy

### For Development
✅ Safe testing environment  
✅ No user impact from bugs  
✅ Easy to debug  
✅ Fast iteration  

### For Production
✅ Stable for users  
✅ Professional setup  
✅ Monitored and reliable  
✅ Separate credentials (security)  

### For You
✅ Test new features on dev app first  
✅ Roll out gradually  
✅ Rollback easily if issues  
✅ Learn from dev before production  

---

## Common Questions

### Q: Can I just change dev app to "Any account" later?
**A**: You could, but it's risky. Better to create a new production app with proper setup.

### Q: Do I need two separate codebases?
**A**: No! Same code, different .env files:
- `.env.development` - Dev app credentials
- `.env.production` - Production app credentials

### Q: What if I want to test with friends?
**A**: Keep dev app "Only on this account" but add them as collaborators to your test repos.

### Q: When should I create production app?
**A**: When you have:
1. Stable deployment (Railway)
2. Custom domain
3. Tested code
4. Ready for real users

---

## Summary

**Current Plan**:
1. ✅ Create dev app with "Only on this account"
2. ✅ Build and test locally
3. ✅ Deploy to Railway (still dev app)
4. ✅ Test thoroughly
5. ✅ Create production app with "Any account"
6. ✅ Launch publicly

**This is NOT a limitation** - it's a best practice for safe development!

---

**Status**: Documentation updated ✅  
**Next**: Register dev app and start building!
