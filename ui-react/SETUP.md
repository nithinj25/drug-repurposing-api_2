# React UI - Quick Start Guide

## 🚀 Quick Setup (5 minutes)

### Step 1: Install Node.js
If you don't have Node.js installed:
- Download from https://nodejs.org/ (LTS version recommended)
- Install and verify: `node --version` and `npm --version`

### Step 2: Install Dependencies
```bash
cd ui-react
npm install
```

### Step 3: Start Development Server
```bash
npm start
```

This automatically opens your browser at `http://localhost:3000`

## 📝 First Analysis

1. **Enter Drug Name**: e.g., "Aspirin"
2. **Enter Indication**: e.g., "Alzheimer's Disease"
3. **Optional Query**: Add research context if needed
4. **Click "Analyze Drug"**
5. **Watch Results**: Real-time polling updates as analysis progresses

## 🔌 Connect to Your API

### Option 1: Render Deployment (Recommended)
- API URL is already set to: `https://drug-repurposing-api.onrender.com`
- Just click "Analyze Drug" and it will connect automatically

### Option 2: Local Development
1. Change API URL to: `http://localhost:8000`
2. Make sure your API server is running locally
3. Submit analysis

The selected URL is saved automatically!

## 📦 Build for Production

When ready to deploy:
```bash
npm run build
```

This creates an optimized `build/` folder ready for deployment.

## 🌐 Deployment Options

### Vercel (Free & Easiest)
```bash
npm install -g vercel
vercel
```

### Netlify (Free)
1. Build: `npm run build`
2. Upload `build/` folder to Netlify

### GitHub Pages
1. Add to package.json: `"homepage": "https://yourusername.github.io/repo"`
2. Install: `npm install --save-dev gh-pages`
3. Add to scripts:
   ```json
   "predeploy": "npm run build",
   "deploy": "gh-pages -d build"
   ```
4. Deploy: `npm run deploy`

## 🆘 Troubleshooting

### Port 3000 already in use?
```bash
# Windows - Kill process on port 3000
netstat -ano | findstr :3000
taskkill /PID <PID> /F

# macOS/Linux
lsof -ti:3000 | xargs kill -9
```

### Dependencies error?
```bash
# Clear npm cache
npm cache clean --force
# Reinstall
rm -rf node_modules package-lock.json
npm install
```

### Can't connect to API?
- Check API URL in the app settings
- Ensure API is running and accessible
- Check browser console (F12) for errors
- Verify CORS is enabled on API

## 📂 Project Structure

```
ui-react/
├── public/           # Static files
├── src/
│   ├── components/   # React components
│   ├── App.js        # Main app
│   ├── App.css       # Styles
│   └── index.js      # Entry point
├── package.json      # Dependencies
└── README.md         # Full documentation
```

## 🎨 Key Features

✅ Real-time job polling
✅ Agent result visualization  
✅ Reasoning analysis display
✅ Modal detail views
✅ Responsive design
✅ API configuration persistence
✅ Professional styling

## 💡 Next Steps

1. ✅ Install and run: `npm install && npm start`
2. ✅ Test with drug analysis
3. ✅ Customize styling in `src/App.css`
4. ✅ Deploy to production

## 📞 Need Help?

- Check browser console (F12) for errors
- Review API logs on Render dashboard
- Ensure API keys are configured: `GROQ_API_KEY`, `USE_GROQ`, `PUBMED_API_KEY`

Happy analyzing! 🎉
