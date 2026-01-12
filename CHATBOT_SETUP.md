# Google AI Studio Chatbot Setup Guide

This guide will help you set up the Google AI Studio (Gemini API) chatbot for your GardenCircle application.

## Prerequisites

1. A Google account
2. Access to Google AI Studio (https://aistudio.google.com/)

## Step 1: Get Your API Key

1. Go to [Google AI Studio](https://aistudio.google.com/)
2. Sign in with your Google account
3. Click on "Get API Key" or navigate to the API keys section
4. Create a new API key (or use an existing one)
5. Copy your API key - you'll need it in the next step

## Step 2: Install Dependencies

Make sure you have the required Python packages installed:

```bash
pip install -r requirements.txt
```

This will install:
- `google-generativeai` - For Google AI Studio (Gemini API)
- `python-dotenv` - For loading `.env` file (already configured)
- Other dependencies (Flask, feedparser, etc.)

## Step 3: Set Environment Variable (Using .env file - Recommended)

The easiest and most secure way is to use a `.env` file. This is already set up for you!

1. **Create a `.env` file** in your project root directory (same level as `requirements.txt`)

2. **Add your API key** to the `.env` file:
   ```
   GOOGLE_AI_STUDIO_API_KEY=your-api-key-here
   ```
   
   Replace `your-api-key-here` with your actual API key from Google AI Studio.

3. **The `.env` file is already configured** - `python-dotenv` is included in `requirements.txt` and the Flask app automatically loads it.

**Important**: The `.env` file is already in `.gitignore`, so it won't be committed to version control.

### Alternative: Set Environment Variable Manually

If you prefer not to use a `.env` file, you can set the environment variable manually:

**Windows (PowerShell):**
```powershell
$env:GOOGLE_AI_STUDIO_API_KEY="your-api-key-here"
```

**Windows (Command Prompt):**
```cmd
set GOOGLE_AI_STUDIO_API_KEY=your-api-key-here
```

**Linux/Mac (Bash):**
```bash
export GOOGLE_AI_STUDIO_API_KEY="your-api-key-here"
```

Note: With manual environment variables, you'll need to set them each time you open a new terminal.

## Step 4: Test the Chatbot

1. Start your Flask application:
   ```bash
   python -m backend.main
   ```

2. Navigate to `http://localhost:5000/chatbot` in your browser
3. Log in if required
4. Try asking a question like: "Ako často mám polievať monstera?"

## Troubleshooting

### Error: "Google AI Studio API key not configured"

- Make sure you've set the `GOOGLE_AI_STUDIO_API_KEY` environment variable
- Restart your Flask application after setting the environment variable
- Check that the API key is correct (no extra spaces or quotes)

### Error: "Google Generative AI library not installed"

- Run: `pip install google-generativeai`
- Make sure you're using the correct Python environment

### Error: "API key is invalid"

- Verify your API key in Google AI Studio
- Make sure the API key hasn't been revoked
- Check that you're using the correct API key format

### Chatbot not responding

- Check your internet connection
- Verify the API key has proper permissions
- Check the browser console for JavaScript errors
- Check the Flask server logs for backend errors

## Security Notes

⚠️ **Important**: Never commit your API key to version control!

- Add `.env` to your `.gitignore` file
- Don't share your API key publicly
- Consider using environment variables or a secrets manager in production

## Features

The chatbot is configured to:
- Respond in Slovak language
- Provide expert advice on plants and gardening
- Answer questions about plant care, identification, and troubleshooting
- Be friendly and informative

## Model Used

The chatbot uses Google's `gemini-pro` model, which is optimized for text generation and conversation.

## Support

If you encounter issues:
1. Check the Flask server logs
2. Check the browser console for errors
3. Verify your API key is valid
4. Make sure all dependencies are installed

