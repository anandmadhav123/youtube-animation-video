# 🎬 Google Flow AI Video Automation Pipeline

यह सिस्टम एक **Master Story / Combined Prompt** लेता है, उसे Google Flow की 8-सेकंड की सीमा के अनुसार **15 से 22 सीन्स** में बाँटता है, Google Flow पर हर सीन को ऑटो-जनरेट करता है, उन्हें एक सीक्वेंशियल 2-3 मिनट के वीडियो में जोड़ता है, और फिर YouTube पर अपलोड करता है।

---

## 🏗️ सिस्टम आर्किटेक्चर (Workflow)

```
[ Master Story Prompt (2-3 Min) ]
                │
                ▼
      ┌──────────────────┐
      │  scene_planner   │ ➔ Gemini AI कहानी को 15-22 सीन्स (8s each) में तोड़ता है
      └──────────────────┘   (Strict Visual Continuity + Lighting + Camera Style)
                │
                ▼
      ┌──────────────────┐
      │  flow_automator  │ ➔ Chrome CDP के ज़रिए flow.google.com पर एक-एक सीन को इनपुट
      └──────────────────┘   करके 8-सेकंड के वीडियो जनरेट करता है
                │
                ▼
      ┌──────────────────┐
      │  video_stitcher  │ ➔ FFmpeg से सभी क्लिप्स को बिना लॉस के जोड़कर 2-3 मिनट का
      └──────────────────┘   फुल-लेंथ MP4 वीडियो तैयार करता है
                │
                ▼
      ┌──────────────────┐
      │ youtube_uploader │ ➔ YouTube Data API v3 से Title, Description, Tags के साथ
      └──────────────────┘   सीधे चैनल पर अपलोड करता है
```

---

## 📁 फ़ाइल संरचना (Project Structure)

*   `main.py` - मास्टर ऑर्केस्ट्रेटर CLI स्क्रिप्ट।
*   `scene_planner.py` - Gemini AI द्वारा प्रॉम्प्ट को 8s सीन्स और YouTube मेटाडेटा में बाँटना।
*   `flow_automator.py` - Playwright Chrome DevTools Protocol (CDP) ऑटोमेशन Google Flow के लिए।
*   `video_stitcher.py` - FFmpeg द्वारा क्लिप्स का त्वरित संयोजन।
*   `youtube_uploader.py` - YouTube Data API v3 अपलोडर।
*   `start_chrome_cdp.sh` - Mac पर Google Chrome को रिमोट डिबगिंग मोड में खोलने की 1-क्लिक स्क्रिप्ट।
*   `config.py` और `.env` - सेटिंग्स और API कीज़।

---

## 🚀 इस्तेमाल करने का तरीका (Step-by-Step Guide)

### 1. क्रेडेंशियल्स सेट करें (.env)
`.env` फ़ाइल खोलें और अपनी API कीज़ भरें:
```ini
GEMINI_API_KEY=your_gemini_api_key_here
FLOW_PROJECT_URL=https://flow.google.com/project/0ebc25ad-8226-4302-a20a-f0728d85d0a2
YOUTUBE_PRIVACY_STATUS=private
```
*(नोट: यदि YouTube अपलोड करना है, तो Google Cloud Console से डाउनलोड की गई OAuth फ़ाइल का नाम `client_secret.json` रखकर इसी फ़ोल्डर में रख दें।)*

### 2. Google Chrome को ऑटोमेशन मोड में शुरू करें
टर्मिनल में यह कमांड चलाएँ:
```bash
./start_chrome_cdp.sh
```
*यह एक Chrome विंडो खोलेगा जो `flow.google.com` पर जाएगी। अगर आप पहली बार चला रहे हैं, तो अपने Google अकाउंट से लॉगिन कर लें।*

### 3. ऑटोमेशन एजेंट चलाएँ
सीधे अपना 2-3 मिनट का प्रॉम्प्ट देकर पाइपलाइन शुरू करें:

```bash
./venv/bin/python main.py --prompt "A breathtaking cinematic journey of an astronaut exploring ancient glowing alien ruins hidden deep under the icy surface of Europa." --minutes 2.5
```

या फिर बिना आर्गुमेंट के चलाएँ और प्रॉम्प्ट टर्मिनल में पेस्ट करें:
```bash
./venv/bin/python main.py
```

### 4. उपयोगी फ्लैग्स (Flags)
*   `--skip-flow` : यदि क्लिप्स पहले से `output/clips/` में मौजूद हैं और केवल सिलाई और YouTube अपलोड करना है।
*   `--skip-upload` : केवल वीडियो बनाकर देखना है, YouTube पर अपलोड नहीं करना है।
*   `--minutes 3.0` : वीडियो की लक्षित अवधि सेट करने के लिए (डिफ़ॉल्ट 2.5 मिनट = लगभग 18-19 सीन्स)।
