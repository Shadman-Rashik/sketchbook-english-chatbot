# 2-minute video script (English only, about 260 words)

Record your phone/screen while the live site is open. Speak slowly and smile.

**0:00–0:15 · Intro (show Splash and Home)**
"Hi, I'm [your name]. This is Sketchbook, an AI English-learning friend for children under seven. The tagline is *Little Words Matter*. Meet Dilly, the doll friend."

**0:15–0:40 · Mood and mode detection (tap 😢, then show the chat)**
"First, Dilly asks how the child feels. If the child feels sad, Dilly switches to a support mode with a calming breathing bubble instead of teaching. The chat shows the detected mode and why. There are four modes: learning, chatting, fun time and support, so it never teaches non-stop."

**0:40–1:05 · Progressive learning (say 'teach me a word', say the word, open Play)**
"When the child asks to learn, Dilly teaches one word at a time. Saying it earns a star. In Play, picture quizzes check answers on the server. Six stars unlock level two, fourteen unlock level three, and the origami crane unfolds."

**1:05–1:25 · CSE Insight (open My Crane)**
"This insight card tracks thinking, feelings, confidence, curiosity and kindness, so a parent sees cognitive and social-emotional growth together."

**1:25–1:50 · Architecture and trade-offs (show docs/architecture.png)**
"The front end is a single page. The back end is Python with Starlette. A safety guard and a mode detector run first, then Groq's Llama 3.1 model writes the reply. If the model is slower than 1.4 seconds, a rule-based brain answers instantly, so responses stay under two seconds. I chose a hosted LLM because a deployed URL cannot use my laptop GPU. SQLite keeps setup simple; the trade-off is that the free disk is ephemeral."

**1:50–2:00 · Close**
"Thanks for watching. The source, design doc and README are in the GitHub repository."
