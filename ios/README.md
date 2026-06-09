# AmbientListen — iOS App

Native SwiftUI app that listens to conversations in the background and extracts tasks, follow-ups, and reminders using Whisper + Claude.

## Requirements

- Mac with Xcode 15+
- iPhone running iOS 16.4+
- [XcodeGen](https://github.com/yonaskolb/XcodeGen) (`brew install xcodegen`)
- OpenAI API key (for Whisper speech-to-text)
- Anthropic API key (for Claude task extraction)

## First-time setup

```bash
cd ios
brew install xcodegen      # one-time
xcodegen generate          # creates AmbientListen.xcodeproj
open AmbientListen.xcodeproj
```

In Xcode:
1. Select the **AmbientListen** target → **Signing & Capabilities**
2. Set **Team** to your personal Apple ID (free account works for sideloading)
3. Connect your iPhone, select it as the run destination
4. Press **⌘R** to build and install

## First launch

Tap the gear icon → enter your OpenAI and Anthropic API keys and your name → Done.

Tap the mic button to start. The app will request microphone permission.

## Background audio

`UIBackgroundModes: audio` is already configured in the project. Once you start listening:
- Lock your phone → the mic keeps recording ✅  
- Switch to another app → the mic keeps recording ✅  
- Force-quit the app → recording stops (expected)

## How it works

1. Records 20-second M4A chunks via `AVAudioRecorder`
2. Each chunk → OpenAI Whisper API for transcription
3. Last ~80 seconds of transcript → Claude analyzes and extracts tasks
4. New items appear in the task list with type + priority labels
5. Tasks persist in `UserDefaults` across app launches
