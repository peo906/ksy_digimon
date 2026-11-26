---
name: gpt-cross-review
description: "디지몬 프롬프트는 나와 GPT가 각각 분석하고, 사용자가 GPT 의견을 공유하면 내가 종합해 최종 프롬프트를 쓴다"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 59d15955-f452-4a78-a2c0-ecf3ba7cd4ae
  modified: 2026-11-26T02:20:03.386Z
---

프롬프트 작성 순서: 1) 나와 GPT가 각각 분석 2) 사용자가 GPT 의견을 나에게 공유 3) 내가 종합해 최종 프롬프트 작성. GPT 의견은 무조건 받아들이지 않고, 공식 디자인과 96칸 가독성 기준으로 골라 반영한다. 반영하지 않은 항목은 이유를 짧게 적는다.

**Why:** 사용자가 "GPT의 제안이니 무조건 수용할 필요 없음"이라고 하며 이 순서를 정함 (2026-11-26).

**How to apply:** 사용자가 표나 제안을 붙여 넣으면 GPT 분석으로 보고 비교 검토한다. 관련: [[official-design-faithful]], [[digipet-sprite-pipeline]]
