# Privacy Policy - court-video-bot

Last updated: 1 November 2026

court-video-bot is a personal tool used by one person (its developer, Swarnjit) to create original videos and upload them to the developer's own
YouTube channels. It is not offered to the public and has no other users.

## YouTube API Services
This tool uses **YouTube API Services** (YouTube Data API v3, method `videos.insert`, scope `https://www.googleapis.com/auth/youtube.upload`).
By using it, the developer is bound by the [YouTube Terms of Service](https://www.youtube.com/t/terms).
Google's use of information is described in the [Google Privacy Policy](https://policies.google.com/privacy).

## What data the tool accesses and stores
- The tool only **uploads** videos that the developer has created. It does **not** read, collect, store, analyse or share any information about
  YouTube viewers, subscribers, comments, or any other user or channel.
- The only credential stored is the OAuth refresh token for the developer's own Google account. It is kept as an encrypted GitHub Actions secret
  and is used only to call `videos.insert`.
- The tool does not use cookies, analytics, advertising or tracking. No data is sold or shared with third parties.

## Retention and deletion
Because no user data is collected, there is nothing else to delete. The stored token is deleted by deleting the GitHub secret.

## Revoking access
Access can be revoked at any time at https://myaccount.google.com/permissions (remove "court-video-bot"), and via the Google security settings
page https://security.google.com/settings/security/permissions. After revocation the tool can no longer upload.

## Contact
swarnjit83@gmail.com
