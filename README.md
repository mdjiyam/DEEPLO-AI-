# AI Chat App — শুধু ফোন দিয়ে (Flutter Web + Python)

কোনো computer লাগবে না। Backend চলবে Render-এ, Flutter web app চলবে GitHub Pages-এ।
দুটোই বিনামূল্যে, আর পুরো কাজ ফোনের browser থেকে।

## ধাপ ১: GitHub-এ code তোলা
1. github.com-এ account খুলুন, নতুন **public** repository বানান (নাম যেমন `chat-app`)।
2. **Add file → Create new file** চেপে নামের ঘরে পুরো path লিখুন (যেমন `backend/main.py`),
   তারপর ফাইলের লেখা paste করে Commit করুন। এভাবে সব ফাইল তুলুন:
   - `backend/main.py`
   - `backend/requirements.txt`
   - `flutter_app/lib/main.dart`
   - `.github/workflows/deploy-web.yml`
   - `render.yaml`
   (`.env.example` তোলার দরকার নেই, আর API key কখনো GitHub-এ রাখবেন না।)

## ধাপ ২: Backend deploy (Render)
1. render.com-এ GitHub দিয়ে login করুন।
2. **New → Blueprint** চাপুন, আপনার repo বেছে নিন (`render.yaml` নিজে থেকে ধরবে)।
3. `GEMINI_API_KEY` চাইলে আপনার বিনামূল্যের key দিন (aistudio.google.com-এ Google account দিয়ে ঢুকে "Get API key" থেকে পাবেন)।
   পরে Claude-এ যেতে চাইলে Render-এর Environment-এ `PROVIDER=claude` আর `ANTHROPIC_API_KEY` যোগ করলেই হবে।
   মডেলের নাম কাজ না করলে AI Studio-তে দেখা মডেলের নাম `GEMINI_MODEL`-এ বসান।
4. Deploy শেষ হলে একটা URL পাবেন, যেমন `https://ai-chat-backend.onrender.com`।
   `…/health` খুলে `{"status":"ok"}` দেখলে ঠিক আছে।

(Free plan-এ কিছুক্ষণ ব্যবহার না হলে server ঘুমিয়ে যায়, প্রথম message-এ ৩০-৫০ সেকেন্ড লাগতে পারে।)

## ধাপ ৩: Flutter web deploy (GitHub Pages)
1. GitHub repo → **Settings → Pages** → Source হিসেবে **GitHub Actions** বেছে নিন।
2. **Settings → Secrets and variables → Actions → Variables** ট্যাবে নতুন variable:
   নাম `BACKEND_URL`, মান Render-এর URL (শেষে `/` ছাড়া)।
3. **Actions** ট্যাবে "Deploy Flutter web to GitHub Pages" workflow খুলে **Run workflow** চাপুন।
4. ৩-৫ মিনিট পর app পাবেন: `https://<আপনার-username>.github.io/<repo-নাম>/`

## ধাপ ৪: ফোনে app-এর মতো রাখা
Chrome-এ link খুলে মেনু (⋮) → **Add to Home screen**।

## পরে কোড বদলালে
GitHub-এ ফাইল edit করে commit করলেই workflow নিজে নতুন build করে দেবে।
