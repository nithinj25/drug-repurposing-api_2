# Drug Repurposing Assistant - React UI

A modern, professional React application for the Drug Repurposing Assistant API. Built with React 18, featuring real-time job polling, interactive agent result visualization, and beautiful UI components.

## 🚀 Features

- **Modern React Architecture**: Built with functional components and React hooks
- **Real-time Analysis**: Auto-polling for job status updates
- **Agent Visualization**: Beautiful cards showing results from 6 specialized agents
- **Reasoning Analysis**: Display AI reasoning with hypothesis and dimension scores
- **Responsive Design**: Works seamlessly on desktop, tablet, and mobile
- **Modal Details**: View full results in expandable modal windows
- **API Configuration**: Switch between local/production APIs with localStorage persistence
- **Loading States**: Skeleton loaders and spinners for better UX

## 📋 Prerequisites

- Node.js 14+ and npm
- React 18+

## 🔧 Installation

1. **Navigate to the React app directory**:
```bash
cd ui-react
```

2. **Install dependencies**:
```bash
npm install
```

## 🏃 Running the App

### Development Mode
```bash
npm start
```
- Opens at `http://localhost:3000`
- Hot-reload enabled
- Browser dev tools integration

### Production Build
```bash
npm run build
```
- Optimized production bundle
- Minified and optimized assets
- Ready for deployment

## 📁 Project Structure

```
ui-react/
├── public/
│   └── index.html              # Root HTML template
├── src/
│   ├── components/
│   │   ├── Header.js           # App header with title
│   │   ├── InputForm.js        # Analysis input form
│   │   ├── ResultsDisplay.js   # Main results container
│   │   ├── ResultCard.js       # Summary card component
│   │   ├── AgentGrid.js        # Agent cards grid
│   │   ├── ReasoningBox.js     # AI reasoning display
│   │   └── DetailsModal.js     # Modal for details view
│   ├── App.js                  # Main app component
│   ├── App.css                 # App styles
│   ├── index.js                # React DOM render
│   ├── index.css               # Global styles
│   └── ...other files
├── package.json                # Dependencies & scripts
└── README.md                   # This file
```

## 🔌 API Configuration

By default, the app connects to:
```
https://drug-repurposing-api.onrender.com
```

To use a local API:
1. Change API endpoint in the form
2. Use `http://localhost:8000` for local development

The selected API URL is saved to browser localStorage for persistence.

## 🎨 Component Overview

### App.js
- Main component managing state and API polling
- Handles job submission and result polling
- Manages modal state for details view

### InputForm.js
- Drug name and indication inputs
- Optional research query textarea
- API endpoint configuration
- Form validation

### ResultsDisplay.js
- Displays job summary, agent results, and reasoning
- Organizes results into logical sections
- Provides access to detailed views

### AgentGrid.js
- Grid layout of 6 agent cards
- Shows agent name, status, and truncated results
- Clickable "View Details" buttons for each agent

### ReasoningBox.js
- Displays AI reasoning hypotheses
- Shows dimension scores as percentages
- Processing time information

### DetailsModal.js
- Full JSON/text display for agent results
- Formatted with syntax highlighting
- Closeable via button or overlay click

## 🌐 API Integration

The app uses the following endpoints:

- **POST /analyze** - Submit drug analysis
  ```json
  {
    "drug_name": "Aspirin",
    "indication": "Alzheimer's Disease",
    "query": "optional research query"
  }
  ```

- **GET /jobs/{job_id}** - Get job status and results
  ```json
  {
    "job_id": "uuid",
    "drug_name": "Aspirin",
    "indication": "Alzheimer's Disease",
    "status": "completed",
    "tasks": {...},
    "reasoning_result": {...}
  }
  ```

## 🎯 Polling Behavior

- **Interval**: 1 second
- **Timeout**: 2 minutes (120 polls)
- **Auto-cancel**: Stops when analysis completes or fails

## 📦 Key Dependencies

- **react** (18.2.0) - UI framework
- **react-dom** (18.2.0) - DOM rendering
- **axios** (1.6.0) - HTTP client (optional, using fetch)
- **react-scripts** (5.0.1) - Build tooling

## 🚢 Deployment

### Vercel (Recommended)
```bash
npm install -g vercel
vercel
```

### Netlify
```bash
npm run build
# Deploy the 'build' folder to Netlify
```

### Azure
```bash
npm run build
# Deploy 'build' folder to Azure Static Web Apps
```

### Docker
```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
```

## 🛠️ Development Tips

- Use React DevTools browser extension for debugging
- Check browser console for API errors
- Use Network tab to inspect API calls
- Component state is managed with `useState`
- Effects handled with `useEffect`

## 🐛 Troubleshooting

### "Cannot reach API"
- Check API endpoint URL in settings
- Verify CORS is enabled on API server
- Ensure API is running and accessible

### "Analysis timeout"
- Increase polling duration in App.js (maxPolls variable)
- Check API server logs for errors
- Verify internet connection

### "Module not found"
- Run `npm install` to ensure all dependencies are installed
- Check import paths in components

## 📝 Environment Variables

Create `.env` file for environment-specific config:
```
REACT_APP_API_URL=https://your-api-url.com
```

Then access in code:
```javascript
const apiUrl = process.env.REACT_APP_API_URL || 'https://drug-repurposing-api.onrender.com';
```

## 🔒 Security

- API key should never be hardcoded in frontend
- Use backend authentication/authorization
- Keep dependencies updated with `npm audit fix`
- Use environment variables for sensitive data

## 📚 Additional Resources

- [React Documentation](https://react.dev)
- [Create React App Guide](https://create-react-app.dev)
- [React Hooks API](https://react.dev/reference/react)

## 📄 License

This project is part of the Drug Repurposing Assistant system.

## 👥 Support

For issues or questions, refer to the main project documentation or contact the development team.
