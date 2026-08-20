import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

export type Language = "en" | "ta" | "te" | "hi";

interface LanguageContextType {
  language: Language;
  setLanguage: (language: Language) => void;
  t: (key: string, variables?: Record<string, string | number>) => string;
}

const translations: Record<Language, Record<string, string>> = {
  en: {
    "additionalDetails.title": "A few optional details, if you have them",
    "additionalDetails.description": "These sharpen the revenue estimate and market read later — skip anything you don't know yet and Continue works either way.",
    "additionalDetails.price.question": "How much will people pay?",
    "additionalDetails.price.free": "Free",
    "additionalDetails.price.5_20": "$5–20/mo",
    "additionalDetails.price.20_100": "$20–100/mo",
    "additionalDetails.price.100_plus": "$100+/mo",
    "additionalDetails.price.notSure": "Not sure yet",
    "additionalDetails.customers.question": "How many customers do you have?",
    "additionalDetails.customers.label": "Initial customer count",
    "additionalDetails.customers.placeholder": "e.g. 10",
    "additionalDetails.geography.question": "Where will you find your first customers?",
    "additionalDetails.geography.unitedStates": "United States",
    "additionalDetails.geography.europe": "Europe",
    "additionalDetails.geography.global": "Global",
    "additionalDetails.geography.other": "Other",
    "additionalDetails.geography.placeholder": "e.g. Southeast Asia",
    "additionalDetails.competitors.question": "Who else is already solving this?",
    "additionalDetails.competitors.label": "Similar products or companies",
    "additionalDetails.competitors.placeholder": "e.g. Uber, Amazon, Google",
    // Who it's for
    "whoItsFor.title": "Who are you building this for?",
    "whoItsFor.mightBeMarket": "You might be building for {industry}",
    "whoItsFor.buildingForMarket": "You are building for {industry}",
    "whoItsFor.hintsQuestion": "Are any of these your customers?",
    "whoItsFor.pickedUpOn": "We picked up on",
    "whoItsFor.question": "Who is your main customer?",
    "whoItsFor.placeholder": "For example: Small restaurant owners…",

    // Opening line
    "idea.opening.question": "What are you building?",

    // Where you are
    "whereYouAre.question": "Where are you right now?",
    "whereYouAre.stage.idea": "Just an idea",
    "whereYouAre.stage.validating": "Validating",
    "whereYouAre.stage.building": "Building",
    "whereYouAre.stage.earlyCustomers": "Early customers",
    "whereYouAre.stage.growing": "Growing",
    "idea.opening.label": "What are you building?",
    "idea.opening.placeholder":
      "A restaurant inventory tool that predicts spoilage before it happens…",
    "idea.opening.nameQuestion": "And what should I call it?",
    "idea.opening.nameLabel": "What should I call it?",
    "idea.opening.namePlaceholder": "WasteLess Kitchen",

    // Problem clarity
    "problem_clarity.question":
      "How well do you understand the problem?",
    "problem_clarity.tip":
      "Think about what the problem is, who faces it, and what makes it difficult for them.",
    "problem_clarity.option.1":
      "I'm still exploring the problem",
    "problem_clarity.option.2":
      "I have a general idea",
    "problem_clarity.option.3":
      "I know the specific problem",
    "problem_clarity.option.4":
      "I know who faces it",
    "problem_clarity.option.5":
      "I understand the pain deeply",

    // Customer pain
    "customer_pain_evidence.question":
      "How do you know people really have this problem?",
    "customer_pain_evidence.tip":
      "Think about conversations, surveys, feedback, or anything you've seen from real people.",
    "customer_pain_evidence.option.1":
      "I haven't checked yet",
    "customer_pain_evidence.option.2":
      "I've talked to a few people",
    "customer_pain_evidence.option.3":
      "I have real feedback or data",

    // Product
    "product_maturity.question":
      "What have you built so far?",
    "product_maturity.tip":
      "Tell us what someone can actually see, try, or use today.",
    "product_maturity.option.1":
      "Just an idea",
    "product_maturity.option.2":
      "I have a prototype or MVP",
    "product_maturity.option.3":
      "People can use it now",

    // Traction
    "traction.question":
      "Are people using it yet?",
    "traction.tip":
      "Users, testers, pilot users, or paying customers all count.",
    "traction.option.1":
      "Not yet",
    "traction.option.2":
      "A few people are trying it",
    "traction.option.3":
      "People are using or paying for it",

    // Revenue
    "revenue_model_clarity.question":
      "How will you make money?",
    "revenue_model_clarity.tip":
      "Tell us how you plan to charge customers or earn revenue.",
    "revenue_model_clarity.option.1":
      "I haven't decided yet",
    "revenue_model_clarity.option.2":
      "I have a basic plan",
    "revenue_model_clarity.option.3":
      "I know how I'll charge",

    // Market
    "market_size_evidence.question":
      "How big could this opportunity be?",
    "market_size_evidence.tip":
      "Give us your best estimate or any market information you have.",
    "market_size_evidence.tipAdvanced":
      "A sourced TAM/SAM/SOM estimate gives the strongest evidence.",
    "market_size_evidence.option.1":
      "I don't know yet",
    "market_size_evidence.option.2":
      "I have a rough idea",
    "market_size_evidence.option.3":
      "I have research or a market estimate",

    // Team
    "team_completeness.question":
      "Does your team have the skills you need?",
    "team_completeness.tip":
      "Think about the skills needed to build, run, and grow your venture.",
    "team_completeness.option.1":
      "I'm missing some skills",
    "team_completeness.option.2":
      "We have some of them",
    "team_completeness.option.3":
      "We have the key skills",

    // Competition
    "competitive_differentiation.question":
      "What makes your idea different?",
    "competitive_differentiation.tip":
      "Think about other solutions and what makes yours better or different.",
    "competitive_differentiation.option.1":
      "I'm not sure yet",
    "competitive_differentiation.option.2":
      "I have some differences",
    "competitive_differentiation.option.3":
      "I have a clear advantage",

    // Shared options
    "skip.not_sure":
      "I'm not sure yet",
    "skip.not_applicable":
      "Not applicable to my venture",

    // Acknowledgements
    "ack.strong":
      "That's strong evidence — noted.",
    "ack.starting":
      "Good — that's a real starting point.",
    "ack.negative":
      "Noted — that's a clear next step to work on, not a flaw in the idea.",
    "ack.unsure":
      "Fair enough — I'll treat that as something worth exploring, not a weakness.",
    "ack.not_applicable":
      "Got it — skipping that one for your venture.",

    // Common
    "common.back":
      "Back",
    "common.continue":
      "Continue",

    // Idea errors
    "idea.error.name":
      "Give it a name before we continue.",
    "idea.error.description":
      "Say a little more — at least {min} characters.",
  },

  ta: {
    "additionalDetails.title": "உங்களிடம் இருந்தால் சில விருப்பத் தகவல்கள்",
    "additionalDetails.description": "இவை பின்னர் வருவாய் மதிப்பீட்டையும் சந்தை பகுப்பாய்வையும் மேம்படுத்தும் — தெரியாதவற்றை தவிர்க்கலாம்; எப்படியும் தொடரலாம்.",
    "additionalDetails.price.question": "மக்கள் எவ்வளவு செலுத்துவார்கள்?",
    "additionalDetails.price.free": "இலவசம்",
    "additionalDetails.price.5_20": "$5–20/மாதம்",
    "additionalDetails.price.20_100": "$20–100/மாதம்",
    "additionalDetails.price.100_plus": "$100+/மாதம்",
    "additionalDetails.price.notSure": "இன்னும் தெரியவில்லை",
    "additionalDetails.customers.question": "உங்களிடம் எத்தனை வாடிக்கையாளர்கள் உள்ளனர்?",
    "additionalDetails.customers.label": "ஆரம்ப வாடிக்கையாளர் எண்ணிக்கை",
    "additionalDetails.customers.placeholder": "எ.கா. 10",
    "additionalDetails.geography.question": "உங்கள் முதல் வாடிக்கையாளர்களை எங்கு கண்டுபிடிப்பீர்கள்?",
    "additionalDetails.geography.unitedStates": "அமெரிக்கா",
    "additionalDetails.geography.europe": "ஐரோப்பா",
    "additionalDetails.geography.global": "உலகளவில்",
    "additionalDetails.geography.other": "மற்றவை",
    "additionalDetails.geography.placeholder": "எ.கா. தென்கிழக்கு ஆசியா",
    "additionalDetails.competitors.question": "வேறு யார் இதே பிரச்சினையைத் தீர்க்கிறார்கள்?",
    "additionalDetails.competitors.label": "ஒத்த தயாரிப்புகள் அல்லது நிறுவனங்கள்",
    "additionalDetails.competitors.placeholder": "எ.கா. Uber, Amazon, Google",
    // Who it's for
    "whoItsFor.title": "நீங்கள் இதை யாருக்காக உருவாக்குகிறீர்கள்?",
    "whoItsFor.mightBeMarket": "நீங்கள் {industry} துறைக்காக உருவாக்கி இருக்கலாம்",
    "whoItsFor.buildingForMarket": "நீங்கள் {industry} துறைக்காக உருவாக்குகிறீர்கள்",
    "whoItsFor.hintsQuestion": "இவர்களில் யாராவது உங்கள் வாடிக்கையாளர்களா?",
    "whoItsFor.pickedUpOn": "உங்கள் யோசனையிலிருந்து கண்டறிந்தது",
    "whoItsFor.question": "உங்கள் முக்கிய வாடிக்கையாளர் யார்?",
    "whoItsFor.placeholder": "உதாரணம்: சிறிய உணவக உரிமையாளர்கள்…",

    // Where you are
    "whereYouAre.question": "நீங்கள் இப்போது எங்கே இருக்கிறீர்கள்?",
    "whereYouAre.stage.idea": "ஒரு யோசனை மட்டுமே",
    "whereYouAre.stage.validating": "சரிபார்த்தல்",
    "whereYouAre.stage.building": "உருவாக்குதல்",
    "whereYouAre.stage.earlyCustomers": "ஆரம்ப வாடிக்கையாளர்கள்",
    "whereYouAre.stage.growing": "வளர்ச்சி",
    "idea.opening.question":
      "நீங்கள் என்ன உருவாக்குகிறீர்கள்?",
    "idea.opening.label":
      "நீங்கள் என்ன உருவாக்குகிறீர்கள்?",
    "idea.opening.placeholder":
      "உணவு கெட்டுப்போவதை முன்கூட்டியே கணிக்கும் உணவக சரக்கு மேலாண்மை கருவி…",
    "idea.opening.nameQuestion":
      "இதற்கு நான் என்ன பெயர் வைக்க வேண்டும்?",
    "idea.opening.nameLabel":
      "இதற்கு என்ன பெயர் வைக்க வேண்டும்?",
    "idea.opening.namePlaceholder":
      "WasteLess Kitchen",

    // Problem clarity
    "problem_clarity.question":
      "பிரச்சனையை நீங்கள் எவ்வளவு நன்றாகப் புரிந்துகொண்டுள்ளீர்கள்?",
    "problem_clarity.tip":
      "பிரச்சனை என்ன, அதை யார் எதிர்கொள்கிறார்கள், அவர்களுக்கு அது ஏன் சிரமமாக உள்ளது என்பதை சிந்தியுங்கள்.",
    "problem_clarity.option.1":
      "நான் இன்னும் பிரச்சனையை ஆராய்ந்து கொண்டிருக்கிறேன்",
    "problem_clarity.option.2":
      "எனக்கு ஒரு பொதுவான யோசனை உள்ளது",
    "problem_clarity.option.3":
      "குறிப்பிட்ட பிரச்சனை எனக்குத் தெரியும்",
    "problem_clarity.option.4":
      "யார் இதை எதிர்கொள்கிறார்கள் என்பது எனக்குத் தெரியும்",
    "problem_clarity.option.5":
      "அவர்களின் சிக்கலை ஆழமாகப் புரிந்துகொண்டுள்ளேன்",

    // Customer pain
    "customer_pain_evidence.question":
      "மக்களுக்கு இந்தப் பிரச்சனை உண்மையில் இருப்பது உங்களுக்கு எப்படித் தெரியும்?",
    "customer_pain_evidence.tip":
      "உரையாடல்கள், கருத்துக்கணிப்புகள், கருத்துகள் அல்லது உண்மையான நபர்களிடமிருந்து கிடைத்த தகவல்களை நினைத்துப் பாருங்கள்.",
    "customer_pain_evidence.option.1":
      "நான் இன்னும் சரிபார்க்கவில்லை",
    "customer_pain_evidence.option.2":
      "நான் சிலரிடம் பேசியுள்ளேன்",
    "customer_pain_evidence.option.3":
      "என்னிடம் உண்மையான கருத்துகள் அல்லது தரவுகள் உள்ளன",

    // Product
    "product_maturity.question":
      "இதுவரை நீங்கள் என்ன உருவாக்கியுள்ளீர்கள்?",
    "product_maturity.tip":
      "இன்று ஒருவர் உண்மையில் பார்க்க, முயற்சிக்க அல்லது பயன்படுத்தக்கூடியதைச் சொல்லுங்கள்.",
    "product_maturity.option.1":
      "ஒரு யோசனை மட்டுமே",
    "product_maturity.option.2":
      "என்னிடம் ஒரு Prototype அல்லது MVP உள்ளது",
    "product_maturity.option.3":
      "மக்கள் இப்போது பயன்படுத்த முடியும்",

    // Traction
    "traction.question":
      "மக்கள் இதைப் பயன்படுத்தத் தொடங்கிவிட்டார்களா?",
    "traction.tip":
      "பயனர்கள், சோதனைப் பயனர்கள், Pilot பயனர்கள் அல்லது பணம் செலுத்தும் வாடிக்கையாளர்கள் அனைவரும் கணக்கில் எடுத்துக்கொள்ளப்படுகிறார்கள்.",
    "traction.option.1":
      "இன்னும் இல்லை",
    "traction.option.2":
      "சிலர் முயற்சி செய்து வருகின்றனர்",
    "traction.option.3":
      "மக்கள் பயன்படுத்துகிறார்கள் அல்லது பணம் செலுத்துகிறார்கள்",

    // Revenue
    "revenue_model_clarity.question":
      "நீங்கள் எப்படி பணம் சம்பாதிப்பீர்கள்?",
    "revenue_model_clarity.tip":
      "வாடிக்கையாளர்களிடம் எப்படி கட்டணம் வசூலிக்கப் போகிறீர்கள் அல்லது வருவாய் ஈட்டப் போகிறீர்கள் என்பதைச் சொல்லுங்கள்.",
    "revenue_model_clarity.option.1":
      "இன்னும் முடிவு செய்யவில்லை",
    "revenue_model_clarity.option.2":
      "என்னிடம் ஒரு அடிப்படை திட்டம் உள்ளது",
    "revenue_model_clarity.option.3":
      "எப்படி கட்டணம் வசூலிப்பேன் என்பது எனக்குத் தெரியும்",

    // Market
    "market_size_evidence.question":
      "இந்த வாய்ப்பு எவ்வளவு பெரியதாக இருக்கலாம்?",
    "market_size_evidence.tip":
      "உங்களுடைய சிறந்த மதிப்பீடு அல்லது சந்தை தொடர்பான தகவலை வழங்குங்கள்.",
    "market_size_evidence.tipAdvanced":
      "ஆதாரங்களுடன் கூடிய TAM/SAM/SOM மதிப்பீடு வலுவான ஆதாரத்தை வழங்கும்.",
    "market_size_evidence.option.1":
      "இன்னும் தெரியவில்லை",
    "market_size_evidence.option.2":
      "எனக்கு ஒரு தோராயமான யோசனை உள்ளது",
    "market_size_evidence.option.3":
      "என்னிடம் ஆராய்ச்சி அல்லது சந்தை மதிப்பீடு உள்ளது",

    // Team
    "team_completeness.question":
      "உங்களுக்குத் தேவையான திறன்கள் உங்கள் குழுவிடம் உள்ளதா?",
    "team_completeness.tip":
      "உங்கள் முயற்சியை உருவாக்க, நடத்த மற்றும் வளர்க்க தேவையான திறன்களை நினைத்துப் பாருங்கள்.",
    "team_completeness.option.1":
      "சில திறன்கள் எங்களிடம் இல்லை",
    "team_completeness.option.2":
      "சில திறன்கள் எங்களிடம் உள்ளன",
    "team_completeness.option.3":
      "முக்கிய திறன்கள் எங்களிடம் உள்ளன",

    // Competition
    "competitive_differentiation.question":
      "உங்கள் யோசனையை வேறுபடுத்துவது என்ன?",
    "competitive_differentiation.tip":
      "மற்ற தீர்வுகள் என்ன, உங்கள் தீர்வு எவ்வாறு சிறந்தது அல்லது வேறுபட்டது என்பதை நினைத்துப் பாருங்கள்.",
    "competitive_differentiation.option.1":
      "எனக்கு இன்னும் உறுதியாகத் தெரியவில்லை",
    "competitive_differentiation.option.2":
      "என்னிடம் சில வேறுபாடுகள் உள்ளன",
    "competitive_differentiation.option.3":
      "என்னிடம் தெளிவான முன்னிலை உள்ளது",

    // Shared
    "skip.not_sure":
      "எனக்கு இன்னும் உறுதியாகத் தெரியவில்லை",
    "skip.not_applicable":
      "என் முயற்சிக்கு இது பொருந்தாது",

    // Acknowledgements
    "ack.strong":
      "இது வலுவான ஆதாரம் — பதிவு செய்துகொண்டோம்.",
    "ack.starting":
      "நல்லது — இது ஒரு நல்ல தொடக்கம்.",
    "ack.negative":
      "பதிவு செய்துகொண்டோம் — இது அடுத்ததாகச் செயல்பட வேண்டிய விஷயம், உங்கள் யோசனையின் குறை அல்ல.",
    "ack.unsure":
      "பரவாயில்லை — இதை ஒரு பலவீனமாக அல்ல, மேலும் ஆராய வேண்டிய விஷயமாக எடுத்துக்கொள்கிறேன்.",
    "ack.not_applicable":
      "புரிந்தது — உங்கள் முயற்சிக்கு இது பொருந்தாததால் தவிர்க்கிறோம்.",

    // Common
    "common.back":
      "பின்செல்",
    "common.continue":
      "தொடரவும்",

    // Errors
    "idea.error.name":
      "தொடர்வதற்கு முன் உங்கள் முயற்சிக்கு ஒரு பெயர் கொடுக்கவும்.",
    "idea.error.description":
      "இன்னும் கொஞ்சம் விளக்குங்கள் — குறைந்தது {min} எழுத்துகள்.",
  },

  te: {
    "additionalDetails.title": "మీ వద్ద ఉంటే కొన్ని ఐచ్ఛిక వివరాలు",
    "additionalDetails.description": "ఇవి తర్వాత ఆదాయ అంచనా మరియు మార్కెట్ విశ్లేషణను మెరుగుపరుస్తాయి — మీకు తెలియని వాటిని దాటవేయండి; ఎలాగైనా కొనసాగించవచ్చు.",
    "additionalDetails.price.question": "ప్రజలు ఎంత చెల్లిస్తారు?",
    "additionalDetails.price.free": "ఉచితం",
    "additionalDetails.price.5_20": "$5–20/నెల",
    "additionalDetails.price.20_100": "$20–100/నెల",
    "additionalDetails.price.100_plus": "$100+/నెల",
    "additionalDetails.price.notSure": "ఇంకా ఖచ్చితంగా తెలియదు",
    "additionalDetails.customers.question": "మీ వద్ద ఎంత మంది కస్టమర్లు ఉన్నారు?",
    "additionalDetails.customers.label": "ప్రారంభ కస్టమర్ల సంఖ్య",
    "additionalDetails.customers.placeholder": "ఉదా. 10",
    "additionalDetails.geography.question": "మీ మొదటి కస్టమర్లను ఎక్కడ కనుగొంటారు?",
    "additionalDetails.geography.unitedStates": "అమెరికా",
    "additionalDetails.geography.europe": "యూరప్",
    "additionalDetails.geography.global": "ప్రపంచవ్యాప్తంగా",
    "additionalDetails.geography.other": "ఇతర",
    "additionalDetails.geography.placeholder": "ఉదా. ఆగ్నేయ ఆసియా",
    "additionalDetails.competitors.question": "ఇప్పటికే దీనిని పరిష్కరిస్తున్న వారు ఎవరు?",
    "additionalDetails.competitors.label": "ఇలాంటి ఉత్పత్తులు లేదా కంపెనీలు",
    "additionalDetails.competitors.placeholder": "ఉదా. Uber, Amazon, Google",
    // Who it's for
    "whoItsFor.title": "మీరు దీన్ని ఎవరి కోసం నిర్మిస్తున్నారు?",
    "whoItsFor.mightBeMarket": "మీరు {industry} కోసం నిర్మిస్తూ ఉండవచ్చు",
    "whoItsFor.buildingForMarket": "మీరు {industry} కోసం నిర్మిస్తున్నారు",
    "whoItsFor.hintsQuestion": "వీరిలో ఎవరైనా మీ కస్టమర్లా?",
    "whoItsFor.pickedUpOn": "మీ ఆలోచనలో గుర్తించినవి",
    "whoItsFor.question": "మీ ప్రధాన కస్టమర్ ఎవరు?",
    "whoItsFor.placeholder": "ఉదాహరణకు: చిన్న రెస్టారెంట్ యజమానులు…",

    // Where you are
    "whereYouAre.question": "మీరు ప్రస్తుతం ఎక్కడ ఉన్నారు?",
    "whereYouAre.stage.idea": "ఒక ఆలోచన మాత్రమే",
    "whereYouAre.stage.validating": "ధృవీకరిస్తున్నాను",
    "whereYouAre.stage.building": "నిర్మిస్తున్నాను",
    "whereYouAre.stage.earlyCustomers": "ప్రారంభ కస్టమర్లు",
    "whereYouAre.stage.growing": "వృద్ధి",

    // Opening line
    "idea.opening.question":
      "మీరు ఏమి నిర్మిస్తున్నారు?",
    "idea.opening.label":
      "మీరు ఏమి నిర్మిస్తున్నారు?",
    "idea.opening.placeholder":
      "ఆహారం పాడవడాన్ని ముందుగానే అంచనా వేసే రెస్టారెంట్ ఇన్వెంటరీ సాధనం…",
    "idea.opening.nameQuestion":
      "దీనికి నేను ఏమని పేరు పెట్టాలి?",
    "idea.opening.nameLabel":
      "దీనికి ఏమని పేరు పెట్టాలి?",
    "idea.opening.namePlaceholder":
      "WasteLess Kitchen",

    // Problem clarity
    "problem_clarity.question":
      "మీరు సమస్యను ఎంతవరకు అర్థం చేసుకున్నారు?",
    "problem_clarity.tip":
      "సమస్య ఏమిటి, దాన్ని ఎవరు ఎదుర్కొంటున్నారు, వారికి అది ఎందుకు కష్టంగా ఉంది అనే విషయాలను ఆలోచించండి.",
    "problem_clarity.option.1":
      "నేను ఇంకా సమస్యను పరిశీలిస్తున్నాను",
    "problem_clarity.option.2":
      "నాకు సాధారణ అవగాహన ఉంది",
    "problem_clarity.option.3":
      "నాకు నిర్దిష్ట సమస్య తెలుసు",
    "problem_clarity.option.4":
      "దాన్ని ఎవరు ఎదుర్కొంటున్నారో నాకు తెలుసు",
    "problem_clarity.option.5":
      "వారి సమస్యను నేను లోతుగా అర్థం చేసుకున్నాను",

    // Customer pain
    "customer_pain_evidence.question":
      "ప్రజలకు ఈ సమస్య నిజంగా ఉందని మీకు ఎలా తెలుసు?",
    "customer_pain_evidence.tip":
      "సంభాషణలు, సర్వేలు, అభిప్రాయాలు లేదా నిజమైన వ్యక్తుల నుండి మీరు తెలుసుకున్న విషయాలను ఆలోచించండి.",
    "customer_pain_evidence.option.1":
      "నేను ఇంకా పరిశీలించలేదు",
    "customer_pain_evidence.option.2":
      "నేను కొంతమందితో మాట్లాడాను",
    "customer_pain_evidence.option.3":
      "నా దగ్గర నిజమైన అభిప్రాయాలు లేదా డేటా ఉన్నాయి",

    // Product
    "product_maturity.question":
      "ఇప్పటివరకు మీరు ఏమి నిర్మించారు?",
    "product_maturity.tip":
      "ప్రస్తుతం ఎవరైనా చూడగల, ప్రయత్నించగల లేదా ఉపయోగించగల దాని గురించి చెప్పండి.",
    "product_maturity.option.1":
      "ఒక ఆలోచన మాత్రమే",
    "product_maturity.option.2":
      "నా దగ్గర Prototype లేదా MVP ఉంది",
    "product_maturity.option.3":
      "ప్రజలు ఇప్పుడు ఉపయోగించగలరు",

    // Traction
    "traction.question":
      "ప్రజలు దీన్ని ఇప్పటికే ఉపయోగిస్తున్నారా?",
    "traction.tip":
      "వినియోగదారులు, టెస్టర్లు, Pilot వినియోగదారులు లేదా చెల్లించే కస్టమర్లు అందరూ లెక్కలోకి వస్తారు.",
    "traction.option.1":
      "ఇంకా లేదు",
    "traction.option.2":
      "కొంతమంది ప్రయత్నిస్తున్నారు",
    "traction.option.3":
      "ప్రజలు ఉపయోగిస్తున్నారు లేదా చెల్లిస్తున్నారు",

    // Revenue
    "revenue_model_clarity.question":
      "మీరు ఎలా డబ్బు సంపాదిస్తారు?",
    "revenue_model_clarity.tip":
      "కస్టమర్లకు ఎలా ఛార్జ్ చేస్తారు లేదా ఆదాయం ఎలా పొందుతారు అనేది చెప్పండి.",
    "revenue_model_clarity.option.1":
      "నేను ఇంకా నిర్ణయించలేదు",
    "revenue_model_clarity.option.2":
      "నాకు ఒక ప్రాథమిక ప్రణాళిక ఉంది",
    "revenue_model_clarity.option.3":
      "ఎలా ఛార్జ్ చేయాలో నాకు తెలుసు",

    // Market
    "market_size_evidence.question":
      "ఈ అవకాశం ఎంత పెద్దదిగా ఉండవచ్చు?",
    "market_size_evidence.tip":
      "మీ ఉత్తమ అంచనా లేదా మీ వద్ద ఉన్న మార్కెట్ సమాచారాన్ని ఇవ్వండి.",
    "market_size_evidence.tipAdvanced":
      "ఆధారాలతో కూడిన TAM/SAM/SOM అంచనా బలమైన సాక్ష్యాన్ని ఇస్తుంది.",
    "market_size_evidence.option.1":
      "నాకు ఇంకా తెలియదు",
    "market_size_evidence.option.2":
      "నాకు ఒక అంచనా ఉంది",
    "market_size_evidence.option.3":
      "నా దగ్గర పరిశోధన లేదా మార్కెట్ అంచనా ఉంది",

    // Team
    "team_completeness.question":
      "మీకు అవసరమైన నైపుణ్యాలు మీ టీమ్‌లో ఉన్నాయా?",
    "team_completeness.tip":
      "మీ వెంచర్‌ను నిర్మించడానికి, నిర్వహించడానికి మరియు అభివృద్ధి చేయడానికి అవసరమైన నైపుణ్యాలను ఆలోచించండి.",
    "team_completeness.option.1":
      "కొన్ని నైపుణ్యాలు మా దగ్గర లేవు",
    "team_completeness.option.2":
      "కొన్ని నైపుణ్యాలు మా దగ్గర ఉన్నాయి",
    "team_completeness.option.3":
      "ముఖ్యమైన నైపుణ్యాలు మా దగ్గర ఉన్నాయి",

    // Competition
    "competitive_differentiation.question":
      "మీ ఆలోచనను ప్రత్యేకంగా చేసేది ఏమిటి?",
    "competitive_differentiation.tip":
      "ఇతర పరిష్కారాలు ఏమిటి, మీ పరిష్కారం ఎలా మెరుగ్గా లేదా భిన్నంగా ఉంది అనేది ఆలోచించండి.",
    "competitive_differentiation.option.1":
      "నాకు ఇంకా ఖచ్చితంగా తెలియదు",
    "competitive_differentiation.option.2":
      "నా దగ్గర కొన్ని తేడాలు ఉన్నాయి",
    "competitive_differentiation.option.3":
      "నాకు స్పష్టమైన ప్రయోజనం ఉంది",

    // Shared
    "skip.not_sure":
      "నాకు ఇంకా ఖచ్చితంగా తెలియదు",
    "skip.not_applicable":
      "నా వెంచర్‌కు ఇది వర్తించదు",

    // Acknowledgements
    "ack.strong":
      "అది బలమైన సాక్ష్యం — నమోదు చేసుకున్నాం.",
    "ack.starting":
      "మంచిది — ఇది మంచి ప్రారంభం.",
    "ack.negative":
      "నమోదు చేసుకున్నాం — ఇది తదుపరి పని చేయాల్సిన విషయం, మీ ఆలోచనలో లోపం కాదు.",
    "ack.unsure":
      "పరవాలేదు — దీన్ని బలహీనతగా కాకుండా మరింతగా పరిశీలించాల్సిన విషయంగా చూస్తాను.",
    "ack.not_applicable":
      "అర్థమైంది — మీ వెంచర్‌కు ఇది వర్తించదు కాబట్టి దాటవేస్తున్నాం.",

    // Common
    "common.back":
      "వెనక్కి",
    "common.continue":
      "కొనసాగించండి",

    // Errors
    "idea.error.name":
      "కొనసాగించే ముందు మీ వెంచర్‌కు ఒక పేరు ఇవ్వండి.",
    "idea.error.description":
      "ఇంకొంచెం వివరించండి — కనీసం {min} అక్షరాలు.",
  },

  hi: {
    "additionalDetails.title": "अगर आपके पास हों तो कुछ वैकल्पिक जानकारी",
    "additionalDetails.description": "ये बाद में राजस्व अनुमान और बाज़ार विश्लेषण को बेहतर बनाएंगी — जो नहीं जानते उसे छोड़ दें; फिर भी आगे बढ़ सकते हैं।",
    "additionalDetails.price.question": "लोग कितना भुगतान करेंगे?",
    "additionalDetails.price.free": "मुफ़्त",
    "additionalDetails.price.5_20": "$5–20/माह",
    "additionalDetails.price.20_100": "$20–100/माह",
    "additionalDetails.price.100_plus": "$100+/माह",
    "additionalDetails.price.notSure": "अभी पक्का नहीं",
    "additionalDetails.customers.question": "आपके पास कितने ग्राहक हैं?",
    "additionalDetails.customers.label": "शुरुआती ग्राहकों की संख्या",
    "additionalDetails.customers.placeholder": "जैसे 10",
    "additionalDetails.geography.question": "आप अपने पहले ग्राहक कहाँ पाएँगे?",
    "additionalDetails.geography.unitedStates": "संयुक्त राज्य अमेरिका",
    "additionalDetails.geography.europe": "यूरोप",
    "additionalDetails.geography.global": "वैश्विक",
    "additionalDetails.geography.other": "अन्य",
    "additionalDetails.geography.placeholder": "जैसे दक्षिण-पूर्व एशिया",
    "additionalDetails.competitors.question": "इस समस्या को पहले से कौन हल कर रहा है?",
    "additionalDetails.competitors.label": "मिलते-जुलते उत्पाद या कंपनियाँ",
    "additionalDetails.competitors.placeholder": "जैसे Uber, Amazon, Google",
    // Who it's for
    "whoItsFor.title": "आप इसे किसके लिए बना रहे हैं?",
    "whoItsFor.mightBeMarket": "शायद आप {industry} के लिए बना रहे हैं",
    "whoItsFor.buildingForMarket": "आप {industry} के लिए बना रहे हैं",
    "whoItsFor.hintsQuestion": "क्या इनमें से कोई आपके ग्राहक हैं?",
    "whoItsFor.pickedUpOn": "आपके आइडिया से पता चला",
    "whoItsFor.question": "आपका मुख्य ग्राहक कौन है?",
    "whoItsFor.placeholder": "उदाहरण: छोटे रेस्तरां मालिक…",

    // Where you are
    "whereYouAre.question": "आप अभी कहाँ हैं?",
    "whereYouAre.stage.idea": "सिर्फ एक आइडिया",
    "whereYouAre.stage.validating": "सत्यापन",
    "whereYouAre.stage.building": "निर्माण",
    "whereYouAre.stage.earlyCustomers": "शुरुआती ग्राहक",
    "whereYouAre.stage.growing": "विकास",
    // Opening line
    "idea.opening.question":
      "आप क्या बना रहे हैं?",
    "idea.opening.label":
      "आप क्या बना रहे हैं?",
    "idea.opening.placeholder":
      "एक रेस्तरां इन्वेंटरी टूल जो खाना खराब होने से पहले उसका अनुमान लगाता है…",
    "idea.opening.nameQuestion":
      "और मुझे इसे क्या नाम देना चाहिए?",
    "idea.opening.nameLabel":
      "मुझे इसे क्या नाम देना चाहिए?",
    "idea.opening.namePlaceholder":
      "WasteLess Kitchen",

    // Problem clarity
    "problem_clarity.question":
      "आप समस्या को कितनी अच्छी तरह समझते हैं?",
    "problem_clarity.tip":
      "सोचें कि समस्या क्या है, इसे कौन झेलता है और उनके लिए यह मुश्किल क्यों है।",
    "problem_clarity.option.1":
      "मैं अभी समस्या को समझने की कोशिश कर रहा हूँ",
    "problem_clarity.option.2":
      "मेरे पास एक सामान्य विचार है",
    "problem_clarity.option.3":
      "मुझे समस्या स्पष्ट रूप से पता है",
    "problem_clarity.option.4":
      "मुझे पता है कि इसे कौन झेलता है",
    "problem_clarity.option.5":
      "मैं उनकी समस्या को गहराई से समझता हूँ",

    // Customer pain
    "customer_pain_evidence.question":
      "आपको कैसे पता है कि लोगों को वास्तव में यह समस्या है?",
    "customer_pain_evidence.tip":
      "बातचीत, सर्वेक्षण, प्रतिक्रिया या वास्तविक लोगों से मिली जानकारी के बारे में सोचें।",
    "customer_pain_evidence.option.1":
      "मैंने अभी तक जाँच नहीं की है",
    "customer_pain_evidence.option.2":
      "मैंने कुछ लोगों से बात की है",
    "customer_pain_evidence.option.3":
      "मेरे पास वास्तविक प्रतिक्रिया या डेटा है",

    // Product
    "product_maturity.question":
      "आपने अब तक क्या बनाया है?",
    "product_maturity.tip":
      "बताएं कि आज कोई व्यक्ति वास्तव में क्या देख, आज़मा या इस्तेमाल कर सकता है।",
    "product_maturity.option.1":
      "सिर्फ एक विचार",
    "product_maturity.option.2":
      "मेरे पास Prototype या MVP है",
    "product_maturity.option.3":
      "लोग इसे अभी इस्तेमाल कर सकते हैं",

    // Traction
    "traction.question":
      "क्या लोग इसे इस्तेमाल कर रहे हैं?",
    "traction.tip":
      "यूज़र्स, टेस्टर्स, पायलट यूज़र्स या भुगतान करने वाले ग्राहक सभी गिने जाते हैं।",
    "traction.option.1":
      "अभी नहीं",
    "traction.option.2":
      "कुछ लोग इसे आज़मा रहे हैं",
    "traction.option.3":
      "लोग इसका इस्तेमाल कर रहे हैं या भुगतान कर रहे हैं",

    // Revenue
    "revenue_model_clarity.question":
      "आप पैसे कैसे कमाएँगे?",
    "revenue_model_clarity.tip":
      "बताएं कि आप ग्राहकों से शुल्क कैसे लेंगे या राजस्व कैसे कमाएँगे।",
    "revenue_model_clarity.option.1":
      "मैंने अभी तय नहीं किया है",
    "revenue_model_clarity.option.2":
      "मेरे पास एक बुनियादी योजना है",
    "revenue_model_clarity.option.3":
      "मुझे पता है कि मैं शुल्क कैसे लूँगा",

    // Market
    "market_size_evidence.question":
      "यह अवसर कितना बड़ा हो सकता है?",
    "market_size_evidence.tip":
      "अपना सबसे अच्छा अनुमान या आपके पास मौजूद बाज़ार की जानकारी दें।",
    "market_size_evidence.tipAdvanced":
      "स्रोतों के साथ TAM/SAM/SOM अनुमान सबसे मजबूत प्रमाण देता है।",
    "market_size_evidence.option.1":
      "मुझे अभी पता नहीं है",
    "market_size_evidence.option.2":
      "मेरे पास एक मोटा अनुमान है",
    "market_size_evidence.option.3":
      "मेरे पास रिसर्च या बाज़ार का अनुमान है",

    // Team
    "team_completeness.question":
      "क्या आपकी टीम के पास ज़रूरी कौशल हैं?",
    "team_completeness.tip":
      "अपने वेंचर को बनाने, चलाने और बढ़ाने के लिए ज़रूरी कौशलों के बारे में सोचें।",
    "team_completeness.option.1":
      "हमारे पास कुछ कौशल नहीं हैं",
    "team_completeness.option.2":
      "हमारे पास कुछ कौशल हैं",
    "team_completeness.option.3":
      "हमारे पास मुख्य कौशल हैं",

    // Competition
    "competitive_differentiation.question":
      "आपके आइडिया को अलग क्या बनाता है?",
    "competitive_differentiation.tip":
      "दूसरे समाधान क्या हैं और आपका समाधान उनसे बेहतर या अलग कैसे है, इसके बारे में सोचें।",
    "competitive_differentiation.option.1":
      "मुझे अभी यकीन नहीं है",
    "competitive_differentiation.option.2":
      "मेरे आइडिया में कुछ अंतर हैं",
    "competitive_differentiation.option.3":
      "मेरे पास एक स्पष्ट बढ़त है",

    // Shared
    "skip.not_sure":
      "मुझे अभी यकीन नहीं है",
    "skip.not_applicable":
      "मेरे वेंचर पर लागू नहीं होता",

    // Acknowledgements
    "ack.strong":
      "यह मजबूत प्रमाण है — नोट कर लिया।",
    "ack.starting":
      "अच्छा — यह एक अच्छी शुरुआत है।",
    "ack.negative":
      "नोट कर लिया — यह अगला कदम है जिस पर काम किया जा सकता है, आपके आइडिया की कमी नहीं।",
    "ack.unsure":
      "ठीक है — मैं इसे कमजोरी नहीं, बल्कि आगे खोजने लायक चीज़ मानूँगा।",
    "ack.not_applicable":
      "समझ गया — आपके वेंचर पर लागू नहीं होने के कारण इसे छोड़ रहे हैं।",

    // Common
    "common.back":
      "वापस",
    "common.continue":
      "जारी रखें",

    // Errors
    "idea.error.name":
      "आगे बढ़ने से पहले अपने वेंचर को एक नाम दें।",
    "idea.error.description":
      "थोड़ा और बताएं — कम से कम {min} अक्षर।",
  },
};

const LanguageContext = createContext<
  LanguageContextType | undefined
>(undefined);

export function LanguageProvider({
  children,
}: {
  children: ReactNode;
}) {
  const [language, setLanguage] = useState<Language>(() => {
    const saved = localStorage.getItem("ventureforge-language");

    if (
      saved === "en" ||
      saved === "ta" ||
      saved === "te" ||
      saved === "hi"
    ) {
      return saved;
    }

    return "en";
  });

  useEffect(() => {
    localStorage.setItem("ventureforge-language", language);
  }, [language]);

  const t = (
    key: string,
    variables: Record<string, string | number> = {},
  ): string => {
    const value =
      translations[language][key] ??
      translations.en[key] ??
      key;

    return value.replace(/\{(\w+)\}/g, (match, variableName) => {
      return variables[variableName] !== undefined
        ? String(variables[variableName])
        : match;
    });
  };

  return (
    <LanguageContext.Provider
      value={{
        language,
        setLanguage,
        t,
      }}
    >
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage(): LanguageContextType {
  const context = useContext(LanguageContext);

  if (!context) {
    throw new Error(
      "useLanguage must be used inside LanguageProvider",
    );
  }

  return context;
}















