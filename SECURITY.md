# Security policy

## Scope

Please report privately anything in the patches or build scripts that could:

- make the patched client send data anywhere other than the RETR0 server on `127.0.0.1`;
- corrupt or leak the player's saves or other app data;
- let input from the network or the text box write outside the app's own files (e.g. the username file);
- make a build script modify the user's original APK or write outside its output folder.

## Reporting

Please **do not open a public issue** for a vulnerability. Use GitHub's **private vulnerability reporting**
("Security" tab → "Report a vulnerability") on this repository, with steps to reproduce.

## Not in scope

The game itself, EA services, and third-party SDKs bundled with the game.
