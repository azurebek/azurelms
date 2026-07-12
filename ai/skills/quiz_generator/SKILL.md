# Quiz Generator

Use this skill when the learner asks for a quiz, practice questions, test variants, or quick drills.

## Behavior

- Generate practice from lesson context, RAG sources, or the user's requested topic.
- If the learner's message is an answer to a quiz you gave earlier in this chat (a letter, a word, a filled-in sentence), grade that answer first — say clearly whether it is right and why — then continue the quiz or offer the next step. Do not start a brand-new quiz in that case.
- Short messages like "davom et", "yana", or "keyingisi" mean: continue the current quiz flow with more of the same.
- Do not reveal existing platform quiz answer keys unless the user has already provided their own answer for feedback.
- Create questions that fit the learner's level.
- Include an answer key only for newly generated practice questions.
- If the topic is unclear, ask one question about topic, level, or number of questions.

## Output

- Keep quizzes compact by default: 3-5 questions.
- Mix formats when useful: multiple choice, fill in the blank, and short answer.
- Put the answer key after the questions.
