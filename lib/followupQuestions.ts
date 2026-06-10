// [챗봇 2차 보정] 정적 객관식 문항 (설계 §6). 동적 분기 없음(범위 밖) — 고정 5문항.
// question 텍스트가 그대로 백엔드 FollowupAnswer.question으로 전달되어 generate
// context_summary의 "[사용자 추가 입력]\n- {question}: {answer}" 줄로 합류한다.

export type FollowupQuestion = {
  id: string;
  question: string;
  options: string[];
};

export const FOLLOWUP_QUESTIONS: FollowupQuestion[] = [
  {
    id: "watering",
    question: "마지막으로 물 준 시점",
    options: ["1일 이내", "3일 이내", "일주일 전", "그 이상", "모름"],
  },
  {
    id: "location",
    question: "주로 두는 위치",
    options: ["남향 창가", "북향 창가", "거실 안쪽", "화장실", "모름"],
  },
  {
    id: "recentChange",
    question: "최근 변화",
    options: ["분갈이", "자리 옮김", "영양제", "없음"],
  },
  {
    id: "drainage",
    question: "화분 밑 배수구",
    options: ["있음", "없음", "모름"],
  },
  {
    id: "ventilation",
    question: "최근 환기",
    options: ["자주", "가끔", "거의 안 함", "모름"],
  },
];
