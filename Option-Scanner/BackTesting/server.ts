import express from 'express';
import { createServer as createViteServer } from 'vite';
import { GoogleGenAI } from '@google/genai';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';

dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const isProd = process.env.NODE_ENV === 'production';
const port = 3000;

async function startServer() {
  const app = express();
  app.use(express.json());

  // API endpoint
  app.post('/api/analyze', async (req, res) => {
    try {
      const { code } = req.body;
      if (!code) {
        return res.status(400).json({ error: 'Python trading algorithm code is required.' });
      }

      const apiKey = process.env.GEMINI_API_KEY;
      if (!apiKey) {
        return res.status(500).json({ error: 'Gemini API key is missing. Please ensure it is set under Settings > Secrets.' });
      }

      const ai = new GoogleGenAI({
        apiKey,
        httpOptions: {
          headers: {
            'User-Agent': 'aistudio-build',
          }
        }
      });

      const prompt = `You are a high-level quant and expert FNO (Futures & Options) Algorithmic Trading Architect with years of experience building ultra-low-latency, error-resilient trading systems.
Analyze the following Python FNO algorithmic trading code for production readiness, options Greeks exposure, critical runtime risks, error-handling loopholes, and capital security.

Provide a comprehensive, highly structure analysis report. You MUST return your response strictly as a single JSON object. Do not wrap the JSON inside a markdown block (e.g. do not use "\`\`\`json").

The returned JSON object must conform EXACTLY to this type:
{
  "safetyScore": number, // Overall safety rating (0-100)
  "executionScore": number, // Order execution safety rating (0-100)
  "errorScore": number, // Real-time error handling resilience rating (0-100)
  "fnoScore": number, // Options and FnO specific risk rating (0-100)
  "recoveryScore": number, // State recovery and restart rating (0-100)
  "summary": string, // A detailed, executive-level 3-4 sentence summary of the code's quality, weaknesses, and potential risk of ruin.
  "criticalFailures": {
    "title": string,
    "description": string,
    "severity": "HIGH" | "CRITICAL" | "MEDIUM"
  }[], // 3-4 high-impact failure scenarios (e.g., "Slippage Loophole", "Unchecked Premium Decay", "Websocket Connection Crash")
  "strengths": string[], // 2-3 design points or positives in the current code
  "greeksAssessed": {
    "delta": string, // Detailed comments on Delta risk handling or hedging controls
    "theta": string, // Theta decay, expiry day margin penalty handling
    "vega": string, // IV crush / spike handling during news events
    "liquidity": string // Spread risk in deep OTM strike pricing
  },
  "greeksNumeric": {
    "delta": number, // Exposure rating (0-100) where high represents higher unhedged risk
    "gamma": number, // Exposure rating (0-100) where high represents higher position acceleration risk
    "theta": number, // Exposure rating (0-100) where high represents higher decay risk or opportunity
    "vega": number, // Exposure rating (0-100) where high represents higher volatility crash risk
    "liquidity": number // Rating (0-100) where high represents higher bid-ask spread or illiquidity threat
  },
  "recommendations": string[], // List of 4-5 concrete architectural improvements to guarantee production safety
  "hardenedCode": string // A fully-developed, production-grade, hardened version of this algorithm or an overlay wrapper in Python that solves key weaknesses, featuring robust try-except loops, exponential backoff, tick sanity assertions, margin reserves, limit order pricing, and error logging.
}

Here corresponds the Python FNO Algorithmic Trading Code:
${code}`;

      const response = await ai.models.generateContent({
        model: 'gemini-3.5-flash',
        contents: prompt,
        config: {
          responseMimeType: "application/json"
        }
      });

      const rawText = response.text || "{}";
      const cleaned = rawText.trim();
      res.json(JSON.parse(cleaned));
    } catch (error: any) {
      console.error('Error in analyze endpoint:', error);
      res.status(500).json({ error: error.message || 'An internal error occurred during the algorithm review.' });
    }
  });

  // Secure workspace python and ledger file downloader endpoint
  app.get('/api/download', (req, res) => {
    try {
      const filename = req.query.file as string;
      if (!filename) {
        return res.status(400).json({ error: 'Filename parameter is required.' });
      }

      const safeName = path.basename(filename);
      const resolvedPath = path.join(process.cwd(), safeName);

      const allowedFiles = [
        'MainEngine.py',
        'Indicators.py',
        'Risk_Engine.py',
        'Option_strategy_core.py',
        'Price_Check.py',
        'RiseFall_sub.py',
        'excel_ledger_orderbook.py',
        'Dhan_Tradehull.py',
        'Monitor_Engine.py',
        'trading_execution_ledger.csv'
      ];

      if (!allowedFiles.includes(safeName)) {
        return res.status(403).json({ error: 'Forbidden file access. Only authorized trading scripts can be fetched.' });
      }

      res.download(resolvedPath, safeName, (err) => {
        if (err) {
          console.error(`Error downloading file ${safeName}:`, err);
          if (!res.headersSent) {
            res.status(404).json({ error: `File ${safeName} could not be retrieved from active workspace.` });
          }
        }
      });
    } catch (e: any) {
      console.error('Download handler server exception:', e);
      res.status(500).json({ error: 'Internal downloading error' });
    }
  });

  if (!isProd) {
    console.log('Running in DEVELOPMENT mode. Starting Vite middleware...');
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa'
    });
    app.use(vite.middlewares);
  } else {
    console.log('Running in PRODUCTION mode. Serving static assets from dist...');
    app.use(express.static(path.join(__dirname, 'dist')));
    app.get('*', (req, res) => {
      res.sendFile(path.join(__dirname, 'dist', 'index.html'));
    });
  }

  app.listen(port, '0.0.0.0', () => {
    console.log(`Express application active on http://0.0.0.0:${port}`);
  });
}

startServer().catch(err => {
  console.error('Fatal initialization error:', err);
});
