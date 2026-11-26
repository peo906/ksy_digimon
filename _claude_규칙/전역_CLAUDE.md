# 공통 지침

- 사용자에게 보이는 모든 글은 한국어로 쓴다. 답변, 질문(AskUserQuestion 포함), 도구 호출 사이의 진행 안내 문장, 도구 설명(description), 협업 메시지 모두 해당한다.
- 영어는 코드, 파일 경로, 명령어, 고유 기술 용어에만 쓴다.
- 최종 결과 보고, 답변 끝 요약 한두 줄(Ponytail 등)도 한국어로 쓴다. 대화 요약(compact)·이어하기 뒤에도 똑같다. 보내기 전에 영어 문장이 섞였는지 확인한다.

# graphify
- **graphify** (`~/.claude/skills/graphify/SKILL.md`) - any input to knowledge graph. Trigger: `/graphify`
When the user types `/graphify`, use the installed graphify skill or instructions before doing anything else.
