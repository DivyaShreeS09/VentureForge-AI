export const en = {
  problem_clarity: {
    question: "How well do you understand the problem?",
    tip: "Think about what the problem is, who faces it, and what makes it difficult for them.",
    options: [
      "I'm still exploring the problem",
      "I have a general idea",
      "I know the specific problem",
      "I know who faces it",
      "I understand the pain deeply",
    ],
  },

  customer_pain_evidence: {
    question: "How do you know people really have this problem?",
    tip: "Think about conversations, surveys, feedback, or anything you've seen from real people.",
    options: [
      "I haven't checked yet",
      "I've talked to a few people",
      "I have real feedback or data",
    ],
  },

  product_maturity: {
    question: "What have you built so far?",
    tip: "Tell us what someone can actually see, try, or use today.",
    options: [
      "Just an idea",
      "I have a prototype or MVP",
      "People can use it now",
    ],
  },

  traction: {
    question: "Are people using it yet?",
    tip: "Users, testers, pilot users, or paying customers all count.",
    options: [
      "Not yet",
      "A few people are trying it",
      "People are using or paying for it",
    ],
  },

  revenue_model_clarity: {
    question: "How will you make money?",
    tip: "Tell us how you plan to charge customers or earn revenue.",
    options: [
      "I haven't decided yet",
      "I have a basic plan",
      "I know how I'll charge",
    ],
  },

  market_size_evidence: {
    question: "How big could this opportunity be?",
    tip: "Give us your best estimate or any market information you have.",
    tipAdvanced: "A sourced TAM/SAM/SOM estimate gives the strongest evidence.",
    options: [
      "I don't know yet",
      "I have a rough idea",
      "I have research or a market estimate",
    ],
  },

  team_completeness: {
    question: "Does your team have the skills you need?",
    tip: "Think about the skills needed to build, run, and grow your venture.",
    options: [
      "I'm missing some skills",
      "We have some of them",
      "We have the key skills",
    ],
  },

  competitive_differentiation: {
    question: "What makes your idea different?",
    tip: "Think about other solutions and what makes yours better or different.",
    options: [
      "I'm not sure yet",
      "I have some differences",
      "I have a clear advantage",
    ],
  },
} as const;