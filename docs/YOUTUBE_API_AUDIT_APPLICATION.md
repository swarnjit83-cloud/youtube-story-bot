# YouTube API compliance audit: application text

Why: videos uploaded through the YouTube Data API by a new Google Cloud project are locked to **private** until the project passes
Google's "YouTube API Services - Audit and Quota Extension" review. Passing it should let `UPLOAD_MODE=api` publish normally.
Approval is not guaranteed; it can take days to weeks. The download package (UPLOAD_MODE=package, the default) works meanwhile.

Form: https://support.google.com/youtube/contact/yt_api_form  (the form's wording changes; if a field below does not exist, skip it)
Sign in with the Google account that owns the Cloud project `court-video-bot`.

## Before you apply (checklist)
- [ ] Google Cloud project `court-video-bot`: OAuth consent screen is "In production" (done), YouTube Data API v3 enabled (done).
- [ ] At least one channel is verified by phone (youtube.com/verify).
- [ ] Privacy policy link works: https://github.com/swarnjit83-cloud/youtube-story-bot/blob/main/PRIVACY.md
- [ ] Project number and project ID ready (Cloud console, dashboard).
- [ ] Prepare 2-3 screenshots: the Actions run log showing an upload line, YouTube Studio showing the uploaded private video,
      and the OAuth consent screen. Do not include secrets in any screenshot.

## Fields to paste (edit the bracketed parts)

**Contact / developer name:** [your name]   **Email:** swarnjit83@gmail.com

**API client / project name:** court-video-bot      **Project number:** [from Cloud console]

**Application website:** https://github.com/swarnjit83-cloud/youtube-story-bot

**Which API services do you use?** YouTube Data API v3, only `videos.insert` (upload a video) with the scope
`https://www.googleapis.com/auth/youtube.upload`. No other YouTube API methods are called.

**Describe your application and use case:**
This is a small personal automation that I run myself on GitHub Actions. It produces original Hindi cartoon videos
(children's learning lessons and fictional stories), made entirely from my own drawings, my own scripts and
synthetic voices. After a video is rendered, the tool uploads it to my own YouTube channels using the YouTube Data API
`videos.insert` method, with the title, description, tags, category and the "made for kids" setting filled in correctly.
Videos are uploaded as private first so that I can review them before publishing. The tool is used only by me, on channels I own.
It is not offered to the public and has no other users.

**How do you use YouTube API data and user data?**
The tool does not read, collect, store or share any data about viewers or other users. The only credential stored is the OAuth
refresh token of my own account, kept as an encrypted GitHub secret and used only to upload my own videos. No YouTube data is
sent to third parties, displayed, cached, or used to build any database.

**Do you comply with the YouTube API Services Terms of Service and Developer Policies?** Yes. The tool uploads only content I
created and own. It respects the "made for kids" declaration for each video, does not circumvent quotas, and does not
automate views, likes, comments or subscriptions.

**Expected usage / quota:** about 2 to 3 uploads per day (1 episode plus 3 Shorts on a channel's scheduled days).
`videos.insert` costs 1,600 units, so the default 10,000-unit daily quota is enough for one episode per day. No quota increase
is requested at this time.

**Privacy policy URL:** https://github.com/swarnjit83-cloud/youtube-story-bot/blob/main/PRIVACY.md

## What to expect
- Google may reply by email with questions or a request for more screenshots. Answer honestly and briefly.
- If it is rejected, read the reason: it often asks for a proper website or a clearer description. Fix and re-apply.
- Do not claim features the tool does not have. This text matches how the tool works today.
- When approved, set the GitHub repository variable `UPLOAD_MODE` to `api` (or `both`) and `YT_PRIVACY` to `public`
  only after you are happy with the first public videos.
