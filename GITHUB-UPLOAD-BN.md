# GitHub-এ আপলোড

ZIP Extract All করুন। ZIP-এর **ভেতরের ফাইল ও ফোল্ডারগুলো** GitHub repository-র মূল জায়গায় রাখুন। GitHub-এর `Add file → Upload files` পৃষ্ঠায় পুরো extracted ফোল্ডারটি টেনে দিন, অথবা `src` ফোল্ডার এবং মূল জায়গার ফাইলগুলো আলাদাভাবে টেনে দিন। শুধু `Choose your files` দিয়ে ফাইল বাছলে `src` ফোল্ডারটি বাদ পড়ে যেতে পারে। ZIP নিজে আপলোড করবেন না।

Commit করার পরে repository-র প্রথম পৃষ্ঠায় নিচেরগুলো সরাসরি দেখা যাবে:

- `src/` (ভেতরে `main.jsx`, `style.css`, `office-logic.js`, `office-presets.json`)
- `Dockerfile`
- `render.yaml`
- `package.json` ও `package-lock.json`
- `server.py` ও `BDRIS_MASTER_GEO.json`

যদি প্রথম পৃষ্ঠায় একটি বাইরের ফোল্ডার দেখা যায় আর এগুলো তার ভেতরে থাকে, তাহলে ফাইলগুলো repository-র root-এ সরিয়ে দিন। Render-এর Root Directory ফাঁকা রাখুন। তারপর Render-এ `Manual Deploy → Deploy latest commit` দিন। Blueprint তৈরি করার সময় `APP_PASSWORD` দিন; `APP_USER` ডিফল্ট `operator`।
