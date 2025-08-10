# Vercel Deployment Guide

## Required Environment Variables

Set these in your Vercel dashboard (`Settings > Environment Variables`):

### Essential Variables
```bash
# Flask Configuration
FLASK_SECRET_KEY=your-secure-random-secret-key-here
LOG_LEVEL=INFO

# OpenAI API
OPENAI_API_KEY=your-openai-api-key

# Encryption (for session security)
ENCRYPTION_KEY=your-base64-encoded-fernet-key

# Cloudinary Storage (for file uploads/CVs)
CLOUDINARY_CLOUD_NAME=your-cloudinary-cloud-name
CLOUDINARY_API_KEY=your-cloudinary-api-key
CLOUDINARY_API_SECRET=your-cloudinary-api-secret

# Vercel Detection (automatically set by Vercel)
VERCEL=1
VERCEL_ENV=production
```

## Generate Required Keys

### Encryption Key
```python
# Run this locally to generate encryption key
from cryptography.fernet import Fernet
import base64

key = Fernet.generate_key()
encoded_key = base64.b64encode(key).decode()
print(f"ENCRYPTION_KEY={encoded_key}")
```

### Flask Secret Key
```python
# Generate secure Flask secret key
import secrets
secret_key = secrets.token_hex(32)
print(f"FLASK_SECRET_KEY={secret_key}")
```

## Cloudinary Setup

1. Create account at [cloudinary.com](https://cloudinary.com)
2. Get credentials from Dashboard
3. Add to Vercel environment variables

## File Storage Changes

### Before (Local/Temp Files)
- ❌ `logging.FileHandler('app_security.log')` 
- ❌ `tempfile.gettempdir()` for uploads
- ❌ `.encryption_key` file
- ❌ Local PDF generation

### After (Serverless Compatible)
- ✅ Console logging (captured by Vercel)
- ✅ Cloudinary for file storage
- ✅ Environment variables for secrets
- ✅ In-memory PDF generation

## Vercel Configuration

### vercel.json
```json
{
  "version": 2,
  "builds": [
    {
      "src": "api/index.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/api/(.*)",
      "dest": "/api/index.py"
    },
    {
      "src": "/(.*)",
      "dest": "/app/$1"
    }
  ],
  "functions": {
    "api/index.py": {
      "maxDuration": 30
    }
  }
}
```

## Deployment Steps

1. **Push code to GitHub**
   ```bash
   git add .
   git commit -m "Add Vercel serverless compatibility"
   git push origin main
   ```

2. **Connect to Vercel**
   - Import project from GitHub
   - Select root directory

3. **Set Environment Variables**
   - Copy all variables from section above
   - Generate keys using provided scripts

4. **Deploy**
   - Vercel will auto-deploy on push
   - Monitor build logs for issues

## Testing Deployment

### Local Testing with Vercel Environment
```bash
# Set environment variables
export VERCEL=1
export VERCEL_ENV=development
export CLOUDINARY_CLOUD_NAME=your-cloud-name
# ... other vars

# Run locally
python api/index.py
```

### Production Testing
1. Upload resume → should use Cloudinary
2. Generate CV → should create Cloudinary URL
3. Download files → should redirect/serve from cloud
4. Check logs → should appear in Vercel dashboard

## Troubleshooting

### Common Issues

**"ENCRYPTION_KEY not set"**
- Add base64-encoded Fernet key to environment

**"Cloudinary not configured"** 
- Verify all 3 Cloudinary variables are set

**"File not found in serverless"**
- File is being stored locally instead of Cloudinary
- Check cv_creator_agent.py uses new storage

**Large response times**
- Enable Vercel Pro for longer function timeouts
- Optimize CV generation process

### Logs & Monitoring
- View logs: Vercel Dashboard → Functions → View Function Logs
- Monitor performance: Use built-in Vercel Analytics
- Error tracking: Logs automatically captured from console

## Security Considerations

- All secrets in environment variables (not files)
- Session encryption keys properly secured
- CORS configured for your domain
- Rate limiting still active
- File access validation maintained

## Backup Strategy

- **Code**: Git repository
- **Files**: Cloudinary provides redundancy  
- **Sessions**: Will reset on deployment (stateless)
- **Logs**: Captured by Vercel platform