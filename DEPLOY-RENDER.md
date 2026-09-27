# React জন্মতথ্য পার্সার অনলাইনে চালানো

এই ফোল্ডারে React v58, Python `/api/parse`, Geo Data এবং Render-এর Dockerfile আছে। একই Web Service সব পরিবেশন করে, তাই API-র আলাদা URL লাগে না।

1. ZIP খুলে ফোল্ডারের **ভেতরের ফাইলগুলো** একটি নতুন private Git repository-র root-এ push করুন। `.env`, API key বা জন্মতথ্য repository-তে রাখবেন না।
2. Render Dashboard-এ **New → Blueprint** নির্বাচন করে repository যুক্ত করুন। `render.yaml` একটি Docker Web Service তৈরি করবে। প্রথমবার তৈরি করার সময় `APP_PASSWORD`-এ নিজের শক্ত পাসওয়ার্ড দিন। লগইন নাম `operator` (প্রয়োজনে Render Environment-এ বদলান)।
3. Deploy শেষ হলে Render-এর `https://....onrender.com/` ঠিকানা খুলুন। ব্রাউজার username/password চাইবে। পৃষ্ঠায় `v58-ascii-english-fields চালু` দেখা গেলে লেখা দিয়ে Parse পরীক্ষা করুন। `/api/health` 200 এবং লগইন করার পর `/api/version` v58 দিতে হবে।
4. শুধু নিয়ম দিয়ে Parse ও Geo Data সঙ্গে সঙ্গে চলে। Ollama বোতাম এই সার্ভারের নিজস্ব Ollama ছাড়া কাজ করবে না। দরকার হলে Render Environment-এ `GROQ_API_KEY` বা `GEMINI_API_KEY` যোগ করুন, অথবা সেশনের API-key ঘরে নিজে লিখুন। Git-এ key রাখবেন না।

Render Free Web Service ১৫ মিনিট অনুরোধ না পেলে থামে; আবার খুললে চালু হতে প্রায় এক মিনিট লাগতে পারে। নিজের যোগ করা অফিস ঠিকানা ব্রাউজারের localStorage-এ থাকে: এক ডিভাইসের ঠিকানা আরেক ডিভাইসে আসে না। মূল ৯টি অফিস এবং ৬৪ জেলার Geo ফাইল Docker image-এ থাকে।

স্থানীয়ভাবে আগের মতো চালাতে `npm start` ব্যবহার করুন; `DEPLOY_MODE=1` কেবল Render-এর জন্য। Render-এ GitHub repository থেকে New → Blueprint ব্যবহার করুন; ZIP সরাসরি Render-এ upload করা যায় না।
