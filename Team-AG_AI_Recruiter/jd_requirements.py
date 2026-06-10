"""
jd_requirements.py
Hardcoded analysis of the Senior AI Engineer JD from Redrob AI.
Since we cannot call LLMs during ranking, all JD requirements are
extracted manually and encoded here with skill synonyms and categories.
"""

# ─── Must-Have Skills ─────────────────────────────────────────────────────────
# These are the skills the JD explicitly says "you absolutely need"
MUST_HAVE_SKILLS = {
    # Embeddings-based retrieval
    "embeddings", "sentence-transformers", "sentence transformers",
    "openai embeddings", "bge", "e5", "embedding", "dense retrieval",
    "semantic search", "vector search", "neural retrieval",
    "text embeddings", "embedding models",

    # Vector databases / hybrid search
    "pinecone", "weaviate", "qdrant", "milvus", "opensearch",
    "elasticsearch", "faiss", "vector database", "vector db",
    "hybrid search", "vector store", "annoy", "chroma", "chromadb",
    "pgvector", "redis vector",

    # Python (strong)
    "python",

    # Ranking evaluation
    "ndcg", "mrr", "map", "ranking evaluation", "a/b testing",
    "evaluation framework", "information retrieval", "search ranking",
    "learning to rank", "retrieval evaluation", "offline evaluation",
    "precision", "recall", "ranking metrics",

    # NLP / IR fundamentals
    "nlp", "natural language processing", "information retrieval",
    "text mining", "text processing", "language models",
    "transformers", "bert", "gpt", "huggingface", "hugging face",
    "tokenization", "text classification", "named entity recognition",
    "ner", "sentiment analysis",

    # ML Production
    "machine learning", "ml", "deep learning", "neural networks",
    "tensorflow", "pytorch", "torch", "keras", "scikit-learn",
    "sklearn", "model deployment", "mlops", "ml engineering",
    "model serving", "model inference", "feature engineering",
    "data pipeline", "ml pipeline",
}

# ─── Nice-to-Have Skills ──────────────────────────────────────────────────────
NICE_TO_HAVE_SKILLS = {
    # LLM fine-tuning
    "lora", "qlora", "peft", "fine-tuning", "fine tuning",
    "finetuning", "llm fine-tuning", "fine-tuning llms",
    "adapter tuning", "instruction tuning", "rlhf",
    "llm", "large language models", "gpt", "llama",
    "langchain", "rag", "retrieval augmented generation",

    # Learning to rank
    "learning to rank", "ltr", "xgboost", "lightgbm",
    "gradient boosting", "catboost", "ranknet", "lambdamart",
    "listwise ranking", "pairwise ranking",

    # HR-tech / recruiting
    "hr-tech", "hrtech", "recruiting", "talent", "ats",
    "applicant tracking", "candidate matching", "job matching",
    "marketplace", "two-sided marketplace",

    # Distributed systems
    "distributed systems", "kafka", "spark", "hadoop",
    "kubernetes", "docker", "microservices", "aws", "gcp",
    "azure", "cloud", "scalability", "high availability",
    "load balancing", "message queue",

    # Open source
    "open source", "open-source", "github", "contributor",
    "maintainer", "oss",

    # Additional strong ML
    "recommendation system", "recommender", "collaborative filtering",
    "content-based filtering", "matrix factorization",
    "reinforcement learning", "bayesian", "optimization",
    "statistical modeling", "time series",
}

# ─── Skill Synonym Map ────────────────────────────────────────────────────────
# Maps variations to canonical form for matching
SKILL_SYNONYMS = {
    "ml": "machine learning",
    "dl": "deep learning",
    "nn": "neural networks",
    "tf": "tensorflow",
    "pt": "pytorch",
    "sk-learn": "scikit-learn",
    "sklearn": "scikit-learn",
    "hf": "huggingface",
    "hugging face": "huggingface",
    "es": "elasticsearch",
    "elastic search": "elasticsearch",
    "open search": "opensearch",
    "vector db": "vector database",
    "vec db": "vector database",
    "sentence-transformers": "sentence transformers",
    "sbert": "sentence transformers",
    "ir": "information retrieval",
    "rec sys": "recommendation system",
    "recsys": "recommendation system",
    "lm": "language models",
    "llm": "large language models",
    "genai": "generative ai",
    "gen ai": "generative ai",
    "fine tuning": "fine-tuning",
    "finetuning": "fine-tuning",
    "k8s": "kubernetes",
    "natural language processing": "nlp",
    "aws sagemaker": "aws",
    "gcp vertex ai": "gcp",
    "azure ml": "azure",
}

# ─── AI/ML Core Skills ────────────────────────────────────────────────────────
# Skills that indicate genuine AI/ML capability (not just keyword listing)
AI_CORE_SKILLS = {
    "machine learning", "deep learning", "nlp", "natural language processing",
    "neural networks", "tensorflow", "pytorch", "transformers",
    "bert", "gpt", "huggingface", "embeddings", "vector database",
    "faiss", "pinecone", "weaviate", "qdrant", "milvus",
    "information retrieval", "search ranking", "recommendation system",
    "reinforcement learning", "computer vision", "image classification",
    "object detection", "gans", "autoencoders", "cnn", "rnn", "lstm",
    "attention mechanism", "fine-tuning", "lora", "qlora", "peft",
    "model deployment", "mlops", "feature engineering", "data pipeline",
    "scikit-learn", "xgboost", "lightgbm", "catboost",
    "statistical modeling", "bayesian", "time series",
    "speech recognition", "tts", "text to speech",
    "rag", "langchain", "llm", "large language models",
    "semantic search", "dense retrieval", "bm25",
    "sentiment analysis", "named entity recognition", "ner",
    "text classification", "text mining", "tokenization",
    "weights & biases", "wandb", "mlflow",
    "bentoml", "seldon", "triton", "onnx",
    "spark mllib", "distributed ml",
}

# ─── Relevant Job Titles ──────────────────────────────────────────────────────
# Titles that indicate relevant experience for this role
HIGHLY_RELEVANT_TITLES = {
    "ai engineer", "senior ai engineer", "lead ai engineer",
    "ml engineer", "senior ml engineer", "lead ml engineer",
    "machine learning engineer", "senior machine learning engineer",
    "nlp engineer", "senior nlp engineer",
    "search engineer", "senior search engineer",
    "ranking engineer", "retrieval engineer",
    "applied scientist", "applied ml scientist",
    "research engineer", "ml research engineer",
    "data scientist", "senior data scientist",
    "deep learning engineer",
    "mlops engineer", "ml platform engineer",
}

SOMEWHAT_RELEVANT_TITLES = {
    "software engineer", "senior software engineer",
    "backend engineer", "senior backend engineer",
    "data engineer", "senior data engineer",
    "analytics engineer", "research scientist",
    "full stack engineer", "platform engineer",
    "infrastructure engineer", "devops engineer",
    "solutions architect", "technical lead",
    "engineering manager", "tech lead",
}

IRRELEVANT_TITLES = {
    "marketing manager", "sales executive", "sales manager",
    "accountant", "senior accountant", "finance manager",
    "hr manager", "human resources", "recruiter",
    "operations manager", "operations director",
    "project manager", "program manager",
    "content writer", "copywriter", "editor",
    "graphic designer", "ui designer", "ux designer",
    "civil engineer", "mechanical engineer",
    "electrical engineer", "chemical engineer",
    "customer support", "customer service",
    "business analyst", "management consultant",
    "product manager",  # borderline — but not what JD wants
    "teacher", "professor", "lecturer",
    "doctor", "nurse", "pharmacist",
    "lawyer", "legal counsel",
}

# ─── Consulting Firms (explicit anti-pattern from JD) ─────────────────────────
CONSULTING_FIRMS = {
    "tcs", "tata consultancy services", "tata consultancy",
    "infosys", "infosys limited", "infosys bpm",
    "wipro", "wipro limited", "wipro technologies",
    "accenture", "accenture solutions",
    "cognizant", "cognizant technology solutions", "cts",
    "capgemini", "capgemini technology",
    "hcl", "hcl technologies", "hcltech",
    "tech mahindra", "tech mahindra limited",
    "mindtree", "ltimindtree", "lti mindtree",
    "mphasis", "hexaware", "persistent systems",
    "l&t infotech", "lti", "larsen & toubro infotech",
    "birlasoft", "zensar", "coforge", "niit technologies",
    "cyient", "sasken", "kpit",
}

# ─── Product Companies (positive signal) ──────────────────────────────────────
NOTABLE_PRODUCT_COMPANIES = {
    "google", "meta", "facebook", "amazon", "microsoft",
    "apple", "netflix", "uber", "airbnb", "twitter", "x corp",
    "linkedin", "salesforce", "adobe", "nvidia", "intel",
    "flipkart", "swiggy", "zomato", "ola", "cred",
    "razorpay", "phonepe", "paytm", "meesho", "zerodha",
    "freshworks", "zoho", "postman", "browserstack",
    "dream11", "myntra", "nykaa", "groww", "jupiter",
    "hasura", "sarvam ai", "krutrim", "ola krutrim",
    "deepmind", "openai", "anthropic", "cohere",
    "hugging face", "huggingface", "stability ai",
    "samsung", "qualcomm", "ibm research",
    "tesla", "bosch", "siemens",
    "stripe", "shopify", "atlassian", "slack",
    "spotify", "snap", "pinterest", "reddit",
    "databricks", "snowflake", "datadog",
    "elastic", "confluent", "mongodb",
}

# ─── Location Preferences ─────────────────────────────────────────────────────
PREFERRED_CITIES = {
    "pune", "noida", "delhi", "delhi ncr", "gurgaon", "gurugram",
    "new delhi",
}

TIER1_INDIAN_CITIES = {
    "bangalore", "bengaluru", "mumbai", "hyderabad",
    "chennai", "kolkata", "ahmedabad",
    "pune", "noida", "delhi", "delhi ncr", "gurgaon", "gurugram",
    "new delhi", "greater noida", "faridabad", "ghaziabad",
}

# ─── CV/Speech/Robotics keywords (anti-pattern if no NLP/IR) ──────────────────
CV_SPEECH_ROBOTICS_SKILLS = {
    "computer vision", "image classification", "object detection",
    "image segmentation", "video processing", "opencv",
    "yolo", "faster rcnn", "resnet", "vgg",
    "speech recognition", "speech synthesis", "tts",
    "text to speech", "asr", "automatic speech recognition",
    "robotics", "ros", "slam", "motion planning",
    "autonomous driving", "self-driving", "lidar",
    "3d reconstruction", "point cloud",
}

NLP_IR_SKILLS = {
    "nlp", "natural language processing", "information retrieval",
    "search", "ranking", "retrieval", "embeddings",
    "text mining", "text classification", "ner",
    "named entity recognition", "sentiment analysis",
    "bert", "gpt", "transformers", "huggingface",
    "semantic search", "vector search", "bm25",
    "recommendation", "langchain", "rag", "llm",
    "question answering", "text generation",
    "pinecone", "weaviate", "qdrant", "milvus", "faiss",
    "elasticsearch", "opensearch",
}

# ─── Production ML Keywords ───────────────────────────────────────────────────
# These in career descriptions indicate real production experience
PRODUCTION_KEYWORDS = {
    "production", "deployed", "deployment", "shipped",
    "real users", "user-facing", "live traffic", "serving",
    "scale", "at scale", "millions", "billions",
    "latency", "throughput", "sla", "uptime",
    "a/b test", "a/b testing", "experiment",
    "monitoring", "alerting", "observability",
    "ci/cd", "pipeline", "infrastructure",
    "api", "microservice", "service",
    "revenue", "engagement", "conversion",
    "platform", "system", "architecture",
}

# ─── Relevant Education Fields ─────────────────────────────────────────────────
RELEVANT_EDUCATION_FIELDS = {
    "computer science", "cs", "artificial intelligence", "ai",
    "machine learning", "data science", "information technology",
    "it", "software engineering", "computational linguistics",
    "mathematics", "statistics", "applied mathematics",
    "electrical engineering", "electronics",
    "information systems", "cognitive science",
}

IRRELEVANT_EDUCATION_FIELDS = {
    "mechanical engineering", "civil engineering",
    "chemical engineering", "architecture",
    "commerce", "accounting", "finance",
    "marketing", "business administration", "mba",
    "arts", "humanities", "literature",
    "law", "medicine", "nursing",
    "agriculture", "textile",
}
