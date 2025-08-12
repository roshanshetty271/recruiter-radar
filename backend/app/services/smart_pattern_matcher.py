"""
Smart Pattern Matcher Service - COMPLETE 1000+ SKILLS VERSION
Fast pattern matching with ALL comprehensive skill/location lists + LLM fallback
"""

import re
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
import logging
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


@dataclass
class MatchResult:
    matched_skill: str
    original_skill: str
    confidence: float
    match_type: str  # "exact", "partial", "fuzzy", "llm_fallback"
    experience_years: Optional[int] = None


class SmartPatternMatcher:
    """Fast pattern matching using ALL 1000+ comprehensive skill lists"""

    def __init__(self):
        self.tech_skills = self._load_all_tech_skills()
        self.locations = self._load_all_locations()
        self.experience_patterns = self._load_experience_patterns()

        # Create lowercase lookup for performance
        self.skills_lower = {skill.lower(): skill for skill in self.tech_skills}
        self.locations_lower = {loc.lower(): loc for loc in self.locations}

        logger.info(
            f"✅ Smart matcher loaded: {len(self.tech_skills)} skills, {len(self.locations)} locations"
        )

    def _load_all_tech_skills(self) -> Set[str]:
        """Load ALL 1000+ comprehensive tech skills list"""

        # Programming Languages (50)
        programming_languages = {
            "Python",
            "Java",
            "JavaScript",
            "TypeScript",
            "C++",
            "C#",
            "Go",
            "Rust",
            "Swift",
            "Kotlin",
            "Ruby",
            "PHP",
            "Scala",
            "R",
            "MATLAB",
            "Julia",
            "Perl",
            "Objective-C",
            "Dart",
            "Elixir",
            "F#",
            "Haskell",
            "Clojure",
            "Groovy",
            "Lua",
            "Erlang",
            "OCaml",
            "Fortran",
            "COBOL",
            "Pascal",
            "Visual Basic",
            "VB.NET",
            "Delphi",
            "Ada",
            "Scheme",
            "Lisp",
            "Prolog",
            "Assembly",
            "VHDL",
            "Verilog",
            "Smalltalk",
            "Crystal",
            "Nim",
            "Zig",
            "V",
            "ReasonML",
            "PureScript",
            "Elm",
            "CoffeeScript",
            "ActionScript",
        }

        # Frontend Technologies (80)
        frontend_technologies = {
            "React",
            "Angular",
            "Vue.js",
            "Svelte",
            "Next.js",
            "Gatsby",
            "Nuxt.js",
            "HTML5",
            "CSS3",
            "Sass",
            "LESS",
            "Stylus",
            "Bootstrap",
            "Tailwind CSS",
            "Material-UI",
            "Ant Design",
            "Chakra UI",
            "Styled Components",
            "Emotion",
            "JSS",
            "jQuery",
            "Backbone.js",
            "Ember.js",
            "Alpine.js",
            "Lit",
            "Stimulus",
            "Redux",
            "MobX",
            "Vuex",
            "Pinia",
            "RxJS",
            "GraphQL",
            "Apollo Client",
            "Relay",
            "Webpack",
            "Parcel",
            "Rollup",
            "Vite",
            "Babel",
            "PostCSS",
            "ESLint",
            "Prettier",
            "Jest",
            "Cypress",
            "Playwright",
            "Puppeteer",
            "Storybook",
            "Figma",
            "Sketch",
            "Adobe XD",
            "Framer",
            "InVision",
            "Zeplin",
            "Abstract",
            "Principle",
            "Marvel",
            "Axure",
            "Balsamiq",
            "WebAssembly",
            "PWA",
            "AMP",
            "Web Components",
            "Shadow DOM",
            "Custom Elements",
            "CSS Grid",
            "Flexbox",
            "CSS Modules",
            "CSS-in-JS",
            "Jamstack",
            "Static Site Generators",
            "Headless CMS",
            "Micro Frontends",
            "Module Federation",
            "Turbopack",
            "SWC",
            "Bun",
            # Add aliases
            "HTML",
            "CSS",
            "React.js",
            "Vue",
            "Angular.js",
            "Next",
            "Gatsby.js",
        }

        # Backend Technologies (80)
        backend_technologies = {
            "Node.js",
            "Express.js",
            "Koa",
            "Fastify",
            "NestJS",
            "Django",
            "Flask",
            "FastAPI",
            "Ruby on Rails",
            "Sinatra",
            "Spring Boot",
            "Spring Framework",
            ".NET Core",
            "ASP.NET",
            "Laravel",
            "Symfony",
            "CodeIgniter",
            "Gin",
            "Echo",
            "Fiber",
            "Phoenix",
            "Actix",
            "Rocket",
            "Warp",
            "Vapor",
            "Perfect",
            "Kitura",
            "Ktor",
            "Micronaut",
            "Quarkus",
            "Helidon",
            "GraphQL",
            "REST API",
            "gRPC",
            "WebSockets",
            "Server-Sent Events",
            "SOAP",
            "JSON-RPC",
            "Apache Kafka",
            "RabbitMQ",
            "Redis",
            "Memcached",
            "Elasticsearch",
            "Solr",
            "Logstash",
            "Kibana",
            "Prometheus",
            "Grafana",
            "Jaeger",
            "Zipkin",
            "OpenTelemetry",
            "Nginx",
            "Apache",
            "IIS",
            "Tomcat",
            "Jetty",
            "Gunicorn",
            "Uvicorn",
            "PM2",
            "Forever",
            "Nodemon",
            "Serverless Framework",
            "AWS Lambda",
            "Azure Functions",
            "Google Cloud Functions",
            "Vercel",
            "Netlify",
            "Railway",
            "Render",
            "Fly.io",
            "API Gateway",
            "Load Balancers",
            "Reverse Proxy",
            "CDN",
            "WAF",
            "Rate Limiting",
            "Circuit Breakers",
            "Service Mesh",
            # Add aliases
            "Node",
            "Express",
            "Spring",
            "Rails",
            "Serverless",
        }

        # Databases (60)
        databases = {
            "PostgreSQL",
            "MySQL",
            "MariaDB",
            "Oracle",
            "SQL Server",
            "SQLite",
            "MongoDB",
            "Cassandra",
            "DynamoDB",
            "Redis",
            "Elasticsearch",
            "Neo4j",
            "ArangoDB",
            "CouchDB",
            "RethinkDB",
            "InfluxDB",
            "TimescaleDB",
            "ClickHouse",
            "Snowflake",
            "BigQuery",
            "Redshift",
            "Azure SQL",
            "Cosmos DB",
            "Firebase Realtime Database",
            "Firestore",
            "FaunaDB",
            "PlanetScale",
            "Supabase",
            "Neon",
            "CockroachDB",
            "YugabyteDB",
            "ScyllaDB",
            "HBase",
            "Accumulo",
            "RocksDB",
            "LevelDB",
            "Berkeley DB",
            "Memcached",
            "Hazelcast",
            "Apache Ignite",
            "GridGain",
            "VoltDB",
            "MemSQL",
            "SingleStore",
            "Greenplum",
            "Vertica",
            "Presto",
            "Trino",
            "Apache Drill",
            "Dremio",
            "Apache Pinot",
            "Apache Druid",
            "QuestDB",
            "VictoriaMetrics",
            "M3DB",
            "OpenTSDB",
            "KairosDB",
            "Graphite",
            "RRDtool",
            # Add aliases
            "Postgres",
            "Mongo",
            "Firebase",
            "SQL",
        }

        # Cloud & DevOps (100)
        cloud_devops = {
            "AWS",
            "Azure",
            "Google Cloud Platform",
            "IBM Cloud",
            "Oracle Cloud",
            "Alibaba Cloud",
            "DigitalOcean",
            "Linode",
            "Vultr",
            "Hetzner",
            "Docker",
            "Kubernetes",
            "OpenShift",
            "Rancher",
            "Nomad",
            "Mesos",
            "Docker Swarm",
            "Podman",
            "containerd",
            "CRI-O",
            "Terraform",
            "Ansible",
            "Puppet",
            "Chef",
            "SaltStack",
            "CloudFormation",
            "ARM Templates",
            "Pulumi",
            "Crossplane",
            "CDK",
            "Jenkins",
            "GitLab CI/CD",
            "GitHub Actions",
            "CircleCI",
            "Travis CI",
            "TeamCity",
            "Bamboo",
            "Drone",
            "Tekton",
            "Argo CD",
            "Flux",
            "Spinnaker",
            "Harness",
            "Octopus Deploy",
            "AWS CodePipeline",
            "Azure DevOps",
            "Google Cloud Build",
            "Buildkite",
            "Concourse CI",
            "Prometheus",
            "Grafana",
            "Datadog",
            "New Relic",
            "AppDynamics",
            "Dynatrace",
            "Splunk",
            "ELK Stack",
            "Fluentd",
            "Logstash",
            "CloudWatch",
            "Azure Monitor",
            "Stackdriver",
            "Nagios",
            "Zabbix",
            "PRTG",
            "SolarWinds",
            "ManageEngine",
            "ServiceNow",
            "PagerDuty",
            "Vault",
            "Consul",
            "etcd",
            "ZooKeeper",
            "AWS IAM",
            "Azure AD",
            "GCP IAM",
            "Okta",
            "Auth0",
            "Keycloak",
            "Helm",
            "Kustomize",
            "Istio",
            "Linkerd",
            "Envoy",
            "NGINX",
            "HAProxy",
            "Traefik",
            "Kong",
            "Zuul",
            # Add aliases
            "GCP",
            "K8s",
            "Git",
            "CI/CD",
            "DevOps",
        }

        # AI & Machine Learning (80)
        ai_ml = {
            "TensorFlow",
            "PyTorch",
            "Keras",
            "Scikit-learn",
            "XGBoost",
            "LightGBM",
            "CatBoost",
            "H2O.ai",
            "MLflow",
            "Kubeflow",
            "OpenAI",
            "GPT-4",
            "ChatGPT",
            "DALL-E",
            "Stable Diffusion",
            "Midjourney",
            "LangChain",
            "LlamaIndex",
            "Hugging Face",
            "Transformers",
            "BERT",
            "RoBERTa",
            "T5",
            "GPT-3",
            "CLIP",
            "Whisper",
            "YOLO",
            "Detectron",
            "OpenCV",
            "MediaPipe",
            "Pandas",
            "NumPy",
            "SciPy",
            "Matplotlib",
            "Seaborn",
            "Plotly",
            "Bokeh",
            "Altair",
            "Streamlit",
            "Gradio",
            "Jupyter",
            "Google Colab",
            "Kaggle",
            "Weights & Biases",
            "Neptune.ai",
            "Comet ML",
            "DVC",
            "Pachyderm",
            "Feast",
            "Tecton",
            "Ray",
            "Dask",
            "Apache Spark",
            "PySpark",
            "Apache Flink",
            "Apache Beam",
            "Airflow",
            "Prefect",
            "Dagster",
            "Luigi",
            "Computer Vision",
            "NLP",
            "NLU",
            "NLG",
            "Speech Recognition",
            "Recommendation Systems",
            "Time Series",
            "Anomaly Detection",
            "AutoML",
            "Feature Engineering",
            "Model Serving",
            "Edge AI",
            "MLOps",
            "AIOps",
            "Explainable AI",
            "Federated Learning",
            "Transfer Learning",
            "Few-shot Learning",
            # Add aliases
            "AI",
            "ML",
            "Machine Learning",
            "Deep Learning",
            "Neural Networks",
        }

        # Data Engineering & Analytics (80)
        data_engineering = {
            "Apache Spark",
            "Databricks",
            "Snowflake",
            "BigQuery",
            "Redshift",
            "Athena",
            "Presto",
            "Trino",
            "Apache Hive",
            "Apache Pig",
            "Apache Kafka",
            "Apache Pulsar",
            "Apache Storm",
            "Apache Samza",
            "Apache Nifi",
            "Confluent",
            "Kinesis",
            "Event Hubs",
            "Pub/Sub",
            "SQS",
            "ETL",
            "ELT",
            "Data Pipeline",
            "Data Lake",
            "Data Warehouse",
            "Data Mesh",
            "Data Fabric",
            "Delta Lake",
            "Apache Iceberg",
            "Apache Hudi",
            "Tableau",
            "Power BI",
            "Looker",
            "Qlik Sense",
            "Sisense",
            "Domo",
            "Grafana",
            "Kibana",
            "Superset",
            "Metabase",
            "SQL",
            "NoSQL",
            "NewSQL",
            "OLAP",
            "OLTP",
            "Data Modeling",
            "Dimensional Modeling",
            "Star Schema",
            "Snowflake Schema",
            "Data Vault",
            "Apache Airflow",
            "Prefect",
            "Dagster",
            "Luigi",
            "Argo Workflows",
            "dbt",
            "Great Expectations",
            "Soda",
            "Monte Carlo",
            "Datadog",
            "Data Quality",
            "Data Governance",
            "Data Catalog",
            "Data Lineage",
            "Apache Atlas",
            "Collibra",
            "Alation",
            "Informatica",
            "Talend",
            "Fivetran",
            "Stitch",
            "Airbyte",
            "Meltano",
            "Singer",
            "Apache Beam",
            "Dataflow",
            "AWS Glue",
            "Azure Data Factory",
            # Add aliases
            "Spark",
            "Kafka",
            "Data Science",
            "Analytics",
            "BI",
        }

        # Cybersecurity (80)
        cybersecurity = {
            "SIEM",
            "SOAR",
            "EDR",
            "XDR",
            "MDR",
            "IDS",
            "IPS",
            "WAF",
            "DDoS Protection",
            "Firewall",
            "Penetration Testing",
            "Vulnerability Assessment",
            "Threat Hunting",
            "Incident Response",
            "Forensics",
            "Malware Analysis",
            "Reverse Engineering",
            "OSINT",
            "CTI",
            "MITRE ATT&CK",
            "Zero Trust",
            "SASE",
            "CASB",
            "DLP",
            "PAM",
            "IAM",
            "MFA",
            "SSO",
            "OAuth",
            "SAML",
            "Encryption",
            "PKI",
            "SSL/TLS",
            "VPN",
            "IPSec",
            "SSH",
            "PGP",
            "AES",
            "RSA",
            "ECC",
            "Splunk",
            "QRadar",
            "ArcSight",
            "Sentinel",
            "Chronicle",
            "Elastic Security",
            "CrowdStrike",
            "SentinelOne",
            "Carbon Black",
            "Cylance",
            "Nessus",
            "Qualys",
            "Rapid7",
            "OpenVAS",
            "Burp Suite",
            "OWASP ZAP",
            "Metasploit",
            "Nmap",
            "Wireshark",
            "tcpdump",
            "ISO 27001",
            "SOC 2",
            "PCI DSS",
            "HIPAA",
            "GDPR",
            "CCPA",
            "NIST",
            "CIS",
            "FISMA",
            "FedRAMP",
            "Security Architecture",
            "DevSecOps",
            "Application Security",
            "Cloud Security",
            "Network Security",
            "Endpoint Security",
            "Mobile Security",
            "IoT Security",
            "Container Security",
            # Add aliases
            "Cybersecurity",
            "InfoSec",
            "Security",
            "Pentesting",
        }

        # Mobile Development (60)
        mobile_development = {
            "iOS",
            "Android",
            "React Native",
            "Flutter",
            "Ionic",
            "Xamarin",
            "NativeScript",
            "Cordova",
            "PhoneGap",
            "Capacitor",
            "Swift",
            "SwiftUI",
            "Objective-C",
            "Kotlin",
            "Java",
            "Dart",
            "JavaScript",
            "TypeScript",
            "C++",
            "Unity",
            "Xcode",
            "Android Studio",
            "Visual Studio",
            "IntelliJ IDEA",
            "AppCode",
            "Firebase",
            "Parse",
            "Realm",
            "Core Data",
            "Room",
            "ARKit",
            "ARCore",
            "Vision",
            "Core ML",
            "TensorFlow Lite",
            "ML Kit",
            "HealthKit",
            "WatchKit",
            "Android Wear",
            "Bluetooth",
            "App Store",
            "Google Play",
            "TestFlight",
            "App Distribution",
            "Crashlytics",
            "Analytics",
            "Push Notifications",
            "Deep Linking",
            "App Clips",
            "Instant Apps",
            "Mobile UI/UX",
            "Material Design",
            "Human Interface Guidelines",
            "Responsive Design",
            "Accessibility",
            "Performance",
            "Battery Optimization",
            "Memory Management",
            "Security",
            "Biometrics",
            # Add aliases
            "Mobile",
            "App Development",
            "Native",
        }

        # Infrastructure & Networking (60)
        infrastructure_networking = {
            "TCP/IP",
            "HTTP/HTTPS",
            "DNS",
            "DHCP",
            "BGP",
            "OSPF",
            "MPLS",
            "VLAN",
            "VPN",
            "SD-WAN",
            "Cisco",
            "Juniper",
            "Arista",
            "Palo Alto",
            "Fortinet",
            "Check Point",
            "F5",
            "Citrix",
            "VMware",
            "Nutanix",
            "Load Balancing",
            "Failover",
            "High Availability",
            "Disaster Recovery",
            "Business Continuity",
            "Backup",
            "Replication",
            "Snapshots",
            "Archive",
            "Retention",
            "Monitoring",
            "Alerting",
            "Logging",
            "Tracing",
            "Metrics",
            "APM",
            "NPM",
            "ITSM",
            "ITOM",
            "AIOps",
            "Data Center",
            "Colocation",
            "Edge Computing",
            "CDN",
            "PoP",
            "Peering",
            "Transit",
            "IX",
            "ASN",
            "CIDR",
            "IPv4",
            "IPv6",
            "NAT",
            "Firewall",
            "Proxy",
            "Reverse Proxy",
            "API Gateway",
            "Service Mesh",
            "Ingress",
            "Egress",
            "Storage",
            "SAN",
            "NAS",
            "Object Storage",
            "Block Storage",
            "File Storage",
            "Backup Storage",
            "Archive Storage",
            "Hybrid Storage",
            "Multi-cloud Storage",
            # Add aliases
            "Networking",
            "Infrastructure",
            "Virtualization",
        }

        # Product & Design (60)
        product_design = {
            "Product Management",
            "Product Owner",
            "Scrum Master",
            "Agile",
            "Scrum",
            "Kanban",
            "SAFe",
            "Lean",
            "Six Sigma",
            "Waterfall",
            "User Research",
            "User Testing",
            "A/B Testing",
            "Analytics",
            "Metrics",
            "KPIs",
            "OKRs",
            "Roadmap",
            "Backlog",
            "Sprint",
            "UI Design",
            "UX Design",
            "Interaction Design",
            "Visual Design",
            "Motion Design",
            "Service Design",
            "Design Systems",
            "Design Thinking",
            "Human-Centered Design",
            "Accessibility",
            "Figma",
            "Sketch",
            "Adobe XD",
            "InVision",
            "Framer",
            "Principle",
            "ProtoPie",
            "Origami",
            "Marvel",
            "Zeplin",
            "Photoshop",
            "Illustrator",
            "After Effects",
            "Premiere Pro",
            "Final Cut Pro",
            "DaVinci Resolve",
            "Cinema 4D",
            "Blender",
            "Maya",
            "3ds Max",
            "Wireframing",
            "Prototyping",
            "Mockups",
            "User Flows",
            "Journey Maps",
            "Personas",
            "Information Architecture",
            "Usability",
            "Heuristics",
            "Best Practices",
            # Add aliases
            "Product",
            "Design",
            "UX",
            "UI",
            "User Experience",
        }

        # Business & Management Tools (60)
        business_tools = {
            "Jira",
            "Confluence",
            "Trello",
            "Asana",
            "Monday.com",
            "Notion",
            "ClickUp",
            "Basecamp",
            "Wrike",
            "Smartsheet",
            "Salesforce",
            "HubSpot",
            "Pipedrive",
            "Zoho CRM",
            "Microsoft Dynamics",
            "SAP",
            "Oracle ERP",
            "NetSuite",
            "Workday",
            "ServiceNow",
            "Slack",
            "Microsoft Teams",
            "Zoom",
            "Google Meet",
            "Discord",
            "Mattermost",
            "Rocket.Chat",
            "Element",
            "Webex",
            "GoToMeeting",
            "Office 365",
            "Google Workspace",
            "Dropbox",
            "Box",
            "OneDrive",
            "SharePoint",
            "Airtable",
            "Coda",
            "Quip",
            "Evernote",
            "QuickBooks",
            "Xero",
            "FreshBooks",
            "Wave",
            "Stripe",
            "PayPal",
            "Square",
            "Braintree",
            "Authorize.Net",
            "Plaid",
            "Zendesk",
            "Intercom",
            "Freshdesk",
            "Help Scout",
            "Drift",
            "Crisp",
            "LiveChat",
            "Olark",
            "Tawk.to",
            "UserVoice",
            # Add aliases
            "CRM",
            "ERP",
            "Project Management",
        }

        # Emerging Technologies (40)
        emerging_tech = {
            "Blockchain",
            "Ethereum",
            "Solidity",
            "Web3",
            "DeFi",
            "NFT",
            "Smart Contracts",
            "Hyperledger",
            "Corda",
            "Polkadot",
            "Quantum Computing",
            "Qiskit",
            "Cirq",
            "Q#",
            "Quantum Algorithms",
            "Quantum Cryptography",
            "Quantum Machine Learning",
            "Quantum Simulation",
            "Quantum Annealing",
            "Quantum Supremacy",
            "AR/VR",
            "Metaverse",
            "Oculus",
            "HoloLens",
            "Magic Leap",
            "Unity",
            "Unreal Engine",
            "A-Frame",
            "Three.js",
            "WebXR",
            "IoT",
            "Edge Computing",
            "MQTT",
            "CoAP",
            "LoRaWAN",
            "Zigbee",
            "Thread",
            "Matter",
            "HomeKit",
            "Alexa",
            # Add aliases
            "AR",
            "VR",
            "Augmented Reality",
            "Virtual Reality",
            "Crypto",
            "Cryptocurrency",
        }

        # Testing & QA (60)
        testing_qa = {
            "Unit Testing",
            "Integration Testing",
            "E2E Testing",
            "Performance Testing",
            "Load Testing",
            "Stress Testing",
            "Security Testing",
            "Accessibility Testing",
            "Usability Testing",
            "Regression Testing",
            "Jest",
            "Mocha",
            "Jasmine",
            "Karma",
            "Enzyme",
            "React Testing Library",
            "Cypress",
            "Playwright",
            "Puppeteer",
            "Selenium",
            "JUnit",
            "TestNG",
            "NUnit",
            "xUnit",
            "MSTest",
            "pytest",
            "unittest",
            "nose2",
            "Robot Framework",
            "Cucumber",
            "JMeter",
            "Gatling",
            "Locust",
            "K6",
            "LoadRunner",
            "BlazeMeter",
            "Artillery",
            "Vegeta",
            "Apache Bench",
            "wrk",
            "Postman",
            "Insomnia",
            "REST Assured",
            "SoapUI",
            "Pact",
            "WireMock",
            "MockServer",
            "Swagger",
            "OpenAPI",
            "AsyncAPI",
            "BrowserStack",
            "Sauce Labs",
            "LambdaTest",
            "CrossBrowserTesting",
            "Appium",
            "Espresso",
            "XCUITest",
            "Detox",
            "Maestro",
            "TestRail",
            # Add aliases
            "Testing",
            "QA",
            "Quality Assurance",
            "Test Automation",
        }

        # Programming Paradigms & Concepts (40)
        programming_concepts = {
            "Object-Oriented Programming",
            "Functional Programming",
            "Procedural Programming",
            "Event-Driven Programming",
            "Reactive Programming",
            "Declarative Programming",
            "Imperative Programming",
            "Logic Programming",
            "Aspect-Oriented Programming",
            "Protocol-Oriented Programming",
            "Design Patterns",
            "SOLID Principles",
            "DRY",
            "KISS",
            "YAGNI",
            "Clean Code",
            "Refactoring",
            "Code Review",
            "Pair Programming",
            "TDD",
            "Algorithms",
            "Data Structures",
            "Big O Notation",
            "Time Complexity",
            "Space Complexity",
            "Recursion",
            "Dynamic Programming",
            "Greedy Algorithms",
            "Graph Algorithms",
            "Sorting",
            "Concurrency",
            "Parallelism",
            "Multithreading",
            "Multiprocessing",
            "Async/Await",
            "Promises",
            "Callbacks",
            "Event Loop",
            "Coroutines",
            "Actor Model",
            # Add aliases
            "OOP",
            "FP",
            "Algorithms",
            "Data Structures",
        }

        # Specialized Domains (60)
        specialized_domains = {
            "FinTech",
            "InsurTech",
            "HealthTech",
            "EdTech",
            "LegalTech",
            "PropTech",
            "AgriTech",
            "FoodTech",
            "TravelTech",
            "RetailTech",
            "Banking",
            "Insurance",
            "Healthcare",
            "Education",
            "Legal",
            "Real Estate",
            "Agriculture",
            "Food & Beverage",
            "Travel",
            "Retail",
            "Payments",
            "Lending",
            "Trading",
            "Wealth Management",
            "Risk Management",
            "Compliance",
            "KYC",
            "AML",
            "RegTech",
            "Open Banking",
            "EHR",
            "EMR",
            "PACS",
            "HL7",
            "FHIR",
            "DICOM",
            "Telemedicine",
            "Digital Health",
            "Medical Devices",
            "Genomics",
            "LMS",
            "MOOC",
            "Adaptive Learning",
            "Gamification",
            "VR Education",
            "AR Education",
            "E-learning",
            "Microlearning",
            "Blended Learning",
            "Flipped Classroom",
            "E-commerce",
            "Marketplace",
            "Omnichannel",
            "POS",
            "Inventory Management",
            "Supply Chain",
            "Logistics",
            "Last Mile",
            "Fulfillment",
            "Returns",
            # Add aliases
            "Fintech",
            "Healthcare",
            "E-commerce",
            "Education",
        }

        # Broader Categories (40)
        broader_categories = {
            "Frontend Development",
            "Backend Development",
            "Full-Stack Development",
            "Mobile Development",
            "DevOps Engineering",
            "Cloud Architecture",
            "Data Engineering",
            "Data Science",
            "Machine Learning Engineering",
            "AI Engineering",
            "Software Engineering",
            "Systems Engineering",
            "Network Engineering",
            "Security Engineering",
            "Platform Engineering",
            "Site Reliability Engineering",
            "Quality Assurance",
            "Test Automation",
            "Performance Engineering",
            "Chaos Engineering",
            "Product Management",
            "Project Management",
            "Program Management",
            "Engineering Management",
            "Technical Leadership",
            "Architecture",
            "Principal Engineering",
            "Staff Engineering",
            "Distinguished Engineering",
            "Fellow",
            "Research",
            "Development",
            "Innovation",
            "R&D",
            "Labs",
            "Incubation",
            "Experimentation",
            "Prototyping",
            "MVP",
            "PoC",
            # Add aliases
            "Full Stack",
            "Full-Stack",
            "Fullstack",
            "Frontend",
            "Backend",
            "DevOps",
            "SRE",
        }

        # Combine all skill sets
        all_skills = (
            programming_languages
            | frontend_technologies
            | backend_technologies
            | databases
            | cloud_devops
            | ai_ml
            | data_engineering
            | cybersecurity
            | mobile_development
            | infrastructure_networking
            | product_design
            | business_tools
            | emerging_tech
            | testing_qa
            | programming_concepts
            | specialized_domains
            | broader_categories
        )

        return all_skills

    def _load_all_locations(self) -> Set[str]:
        """Load ALL comprehensive locations list"""

        # All 50 US States + DC
        states_full = {
            "Alabama",
            "Alaska",
            "Arizona",
            "Arkansas",
            "California",
            "Colorado",
            "Connecticut",
            "Delaware",
            "Florida",
            "Georgia",
            "Hawaii",
            "Idaho",
            "Illinois",
            "Indiana",
            "Iowa",
            "Kansas",
            "Kentucky",
            "Louisiana",
            "Maine",
            "Maryland",
            "Massachusetts",
            "Michigan",
            "Minnesota",
            "Mississippi",
            "Missouri",
            "Montana",
            "Nebraska",
            "Nevada",
            "New Hampshire",
            "New Jersey",
            "New Mexico",
            "New York",
            "North Carolina",
            "North Dakota",
            "Ohio",
            "Oklahoma",
            "Oregon",
            "Pennsylvania",
            "Rhode Island",
            "South Carolina",
            "South Dakota",
            "Tennessee",
            "Texas",
            "Utah",
            "Vermont",
            "Virginia",
            "Washington",
            "West Virginia",
            "Wisconsin",
            "Wyoming",
            "District of Columbia",
        }

        # State abbreviations
        state_abbrev = {
            "AL",
            "AK",
            "AZ",
            "AR",
            "CA",
            "CO",
            "CT",
            "DE",
            "FL",
            "GA",
            "HI",
            "ID",
            "IL",
            "IN",
            "IA",
            "KS",
            "KY",
            "LA",
            "ME",
            "MD",
            "MA",
            "MI",
            "MN",
            "MS",
            "MO",
            "MT",
            "NE",
            "NV",
            "NH",
            "NJ",
            "NM",
            "NY",
            "NC",
            "ND",
            "OH",
            "OK",
            "OR",
            "PA",
            "RI",
            "SC",
            "SD",
            "TN",
            "TX",
            "UT",
            "VT",
            "VA",
            "WA",
            "WV",
            "WI",
            "WY",
            "DC",
        }

        # US Territories
        territories = {
            "Puerto Rico",
            "PR",
            "US Virgin Islands",
            "VI",
            "American Samoa",
            "AS",
            "Guam",
            "GU",
            "Northern Mariana Islands",
            "MP",
        }

        # Major US Cities (Top 50)
        major_cities = {
            "New York City",
            "Los Angeles",
            "Chicago",
            "Houston",
            "Phoenix",
            "Philadelphia",
            "San Antonio",
            "San Diego",
            "Dallas",
            "San Jose",
            "Austin",
            "Jacksonville",
            "Fort Worth",
            "Columbus",
            "Charlotte",
            "San Francisco",
            "Indianapolis",
            "Seattle",
            "Denver",
            "Washington DC",
            "Boston",
            "El Paso",
            "Nashville",
            "Detroit",
            "Oklahoma City",
            "Portland",
            "Las Vegas",
            "Memphis",
            "Louisville",
            "Baltimore",
            "Milwaukee",
            "Albuquerque",
            "Tucson",
            "Fresno",
            "Mesa",
            "Sacramento",
            "Atlanta",
            "Kansas City",
            "Colorado Springs",
            "Omaha",
            "Raleigh",
            "Miami",
            "Long Beach",
            "Virginia Beach",
            "Oakland",
            "Minneapolis",
            "Tulsa",
            "Tampa",
            "Arlington",
            "New Orleans",
        }

        # Additional common location terms
        location_terms = {
            "Remote",
            "Worldwide",
            "Global",
            "USA",
            "United States",
            "US",
            "America",
            "Hybrid",
            "Work from Home",
            "WFH",
            "On-site",
            "Onsite",
            "Bay Area",
            "Silicon Valley",
            "SoCal",
            "NorCal",
            "NYC",
            "LA",
            "SF",
            "DMV",
            "Tri-State",
            "Pacific Northwest",
            "East Coast",
            "West Coast",
            "Midwest",
            "Southeast",
            "Southwest",
            "Northeast",
            "Mountain West",
        }

        return states_full | state_abbrev | territories | major_cities | location_terms

    def _load_experience_patterns(self) -> List[Tuple[str, str]]:
        """Load comprehensive experience extraction patterns"""
        return [
            # Standard years patterns
            (r"(\d+)\s*\+?\s*years?\s+(?:of\s+)?(?:experience|exp)", "years_first"),
            (
                r"(?:over|more\s+than|minimum|at\s+least|above)\s+(\d+)\s*\+?\s*years?",
                "over_years",
            ),
            (r"(\d+)\s*to\s*(\d+)\s*years?", "range_years"),
            (r"(\d+)\s*\+\s*years?", "plus_years"),
            (r"(\d+)\s*-\s*(\d+)\s*years?", "range_years_dash"),
            # Skill + experience patterns
            (
                r"(\w+(?:\.\w+)?)\s+.*?(?:over|with|having|minimum)\s+(\d+)\s*\+?\s*years?",
                "skill_with_years",
            ),
            (r"(\d+)\s*\+?\s*years?\s+(?:of\s+)?(\w+(?:\.\w+)?)", "years_of_skill"),
            (
                r"need\s+.*?(\w+(?:\.\w+)?)\s+.*?(\d+)\s*\+?\s*years?",
                "need_skill_years",
            ),
            (
                r"(\w+(?:\.\w+)?)\s+(?:developer|engineer|programmer)\s+with\s+(\d+)\s*\+?\s*years?",
                "role_with_years",
            ),
            (
                r"(\d+)\s*\+?\s*years?\s+(\w+(?:\.\w+)?)\s+(?:developer|engineer|programmer)",
                "years_role",
            ),
            # Seniority patterns (map to years)
            (r"senior|sr\.|lead", "senior"),
            (r"junior|jr\.|entry.?level|graduate|new.grad", "junior"),
            (r"principal|staff|architect|distinguished", "principal"),
            (r"mid.?level|intermediate", "mid"),
            # Alternative experience expressions
            (r"(\d+)\s*\+?\s*yrs?", "years_abbrev"),
            (r"(\d+)\s*years?\s+exp(?:erience)?", "years_exp"),
        ]

    async def extract_skills_from_query(self, query: str) -> List[MatchResult]:
        """Extract skills using comprehensive fast matching with LLM fallback"""
        query_lower = query.lower().strip()
        matches = []

        # Step 1: Find all potential skill mentions in query
        potential_skills = self._find_potential_skills(query_lower)

        for potential_skill in potential_skills:
            match_result = await self._match_skill(potential_skill, query_lower)
            if match_result:
                matches.append(match_result)

        # Step 2: If no skills found, try LLM fallback
        if not matches:
            logger.info(
                "🧠 No skills found in comprehensive lists - trying LLM fallback"
            )
            llm_result = await self._llm_skill_extraction_fallback(query)
            if llm_result:
                matches.extend(llm_result)

        # Remove duplicates and sort by confidence
        unique_matches = self._deduplicate_matches(matches)
        return sorted(unique_matches, key=lambda x: x.confidence, reverse=True)

    def _find_potential_skills(self, query: str) -> List[str]:
        """Extract potential skill words from query using comprehensive patterns"""
        # Enhanced skill patterns for better extraction
        skill_patterns = [
            # Role-based patterns
            r"(\w+(?:\.\w+)?(?:\s+\w+)?)\s+(?:developer|engineer|programmer|specialist|expert|architect|admin|administrator)",
            r"(?:senior|junior|lead|principal)\s+(\w+(?:\.\w+)?(?:\s+\w+)?)\s+(?:developer|engineer|programmer)",
            # Skill mention patterns
            r"(?:with|having|using|knows?|skilled\s+in|proficient\s+in|experience\s+with)\s+(\w+(?:\.\w+)?(?:\s+\w+)?)",
            r"(?:show|find|need|want|looking\s+for)\s+(?:me\s+)?(\w+(?:\.\w+)?(?:\s+\w+)?)",
            r"(\w+(?:\.\w+)?(?:\s+\w+)?)\s+(?:skills?|experience|expertise|knowledge|background)",
            r"(\w+(?:\.\w+)?(?:\s+\w+)?)\s+(?:framework|library|platform|stack|tool)",
            # Technology stack patterns
            r"(?:using|built\s+with|working\s+with|stack\s+includes?)\s+(\w+(?:\.\w+)?(?:\s+\w+)?)",
            r"(\w+(?:\.\w+)?(?:\s+\w+)?)\s+(?:and|,|\+|/)",
            # Job description patterns
            r"position\s+for\s+(\w+(?:\.\w+)?(?:\s+\w+)?)",
            r"role\s+for\s+(\w+(?:\.\w+)?(?:\s+\w+)?)",
        ]

        potential_skills = set()

        # Extract from patterns
        for pattern in skill_patterns:
            matches = re.finditer(pattern, query, re.IGNORECASE)
            for match in matches:
                skill = match.group(1).strip()
                if len(skill) > 1 and not self._is_common_word(skill):
                    potential_skills.add(skill)

        # Also check individual words that might be skills
        words = re.findall(r"\b\w+(?:\.\w+)?\b", query)
        for word in words:
            if len(word) > 2 and not self._is_common_word(word):
                potential_skills.add(word)

        return list(potential_skills)

    def _is_common_word(self, word: str) -> bool:
        """Filter out common English words that aren't skills"""
        common_words = {
            "the",
            "and",
            "for",
            "with",
            "are",
            "have",
            "will",
            "can",
            "who",
            "what",
            "when",
            "where",
            "how",
            "why",
            "need",
            "want",
            "looking",
            "show",
            "find",
            "get",
            "make",
            "take",
            "come",
            "years",
            "experience",
            "work",
            "team",
            "company",
            "project",
            "position",
            "role",
            "job",
        }
        return word.lower() in common_words

    async def _match_skill(
        self, potential_skill: str, query: str
    ) -> Optional[MatchResult]:
        """Match a potential skill against comprehensive skill lists"""
        potential_lower = potential_skill.lower()

        # 1. Exact match
        if potential_lower in self.skills_lower:
            experience = self._extract_experience_for_skill(potential_skill, query)
            return MatchResult(
                matched_skill=self.skills_lower[potential_lower],
                original_skill=potential_skill,
                confidence=1.0,
                match_type="exact",
                experience_years=experience,
            )

        # 2. Partial match (html matches html5, react matches react.js)
        for skill_lower, skill_proper in self.skills_lower.items():
            # Check both directions: "html" in "html5" and "html5" in "html"
            if potential_lower in skill_lower or skill_lower in potential_lower:
                # Additional validation - length should be reasonable
                if abs(len(potential_lower) - len(skill_lower)) <= 5:
                    experience = self._extract_experience_for_skill(
                        potential_skill, query
                    )
                    confidence = 0.9 if potential_lower in skill_lower else 0.8
                    return MatchResult(
                        matched_skill=skill_proper,
                        original_skill=potential_skill,
                        confidence=confidence,
                        match_type="partial",
                        experience_years=experience,
                    )

        # 3. Fuzzy match (for typos, variations)
        best_match = None
        best_ratio = 0.0

        for skill_lower, skill_proper in self.skills_lower.items():
            ratio = SequenceMatcher(None, potential_lower, skill_lower).ratio()
            if ratio > best_ratio and ratio > 0.85:  # 85% similarity threshold
                best_ratio = ratio
                best_match = skill_proper

        if best_match:
            experience = self._extract_experience_for_skill(potential_skill, query)
            return MatchResult(
                matched_skill=best_match,
                original_skill=potential_skill,
                confidence=best_ratio,
                match_type="fuzzy",
                experience_years=experience,
            )

        return None

    def _extract_experience_for_skill(self, skill: str, query: str) -> Optional[int]:
        """Extract experience years specifically for this skill"""
        skill_lower = skill.lower()

        for pattern, pattern_type in self.experience_patterns:
            if pattern_type in ["senior", "junior", "principal", "mid"]:
                # Map seniority to years
                if re.search(pattern, query, re.IGNORECASE) and skill_lower in query:
                    seniority_to_years = {
                        "junior": 1,
                        "mid": 3,
                        "senior": 5,
                        "principal": 8,
                    }
                    return seniority_to_years.get(pattern_type, None)
                continue

            matches = re.finditer(pattern, query, re.IGNORECASE)
            for match in matches:
                # Check if this experience is related to our skill
                context_start = max(0, match.start() - 50)
                context_end = min(len(query), match.end() + 50)
                context = query[context_start:context_end].lower()

                if skill_lower in context:
                    # Extract the number
                    numbers = [int(g) for g in match.groups() if g and g.isdigit()]
                    if numbers:
                        if pattern_type == "range_years" and len(numbers) >= 2:
                            return numbers[0]  # Use minimum of range
                        return numbers[0]  # Return first number found

        return None

    def _deduplicate_matches(self, matches: List[MatchResult]) -> List[MatchResult]:
        """Remove duplicate matches, keeping highest confidence"""
        seen = {}
        for match in matches:
            key = match.matched_skill.lower()
            if key not in seen or match.confidence > seen[key].confidence:
                seen[key] = match
        return list(seen.values())

    async def _llm_skill_extraction_fallback(self, query: str) -> List[MatchResult]:
        """LLM fallback for unknown skills (placeholder)"""
        # TODO: Implement LLM fallback if needed for truly unknown skills
        logger.warning(
            f"🤖 LLM fallback needed for query: '{query}' (implement if required)"
        )
        return []

    def extract_location(self, query: str) -> Optional[str]:
        """Extract location using comprehensive location matching"""
        query_lower = query.lower()

        # Enhanced location patterns
        location_patterns = [
            r"in\s+([A-Z][a-zA-Z\s,\-\.]+?)(?:\s|$|,|\.|!|\?)",
            r"(?:from|based\s+in|located\s+in|working\s+from)\s+([A-Z][a-zA-Z\s,\-\.]+?)(?:\s|$|,|\.|!|\?)",
            r"\b(remote|Remote|REMOTE)\b",
            r"(?:^|\s)(remote)(?:\s|$|,|\.|!|\?)",
            r"([A-Z]{2})\s+(?:based|area|region)",  # State abbreviations
        ]

        for pattern in location_patterns:
            match = re.search(pattern, query)
            if match:
                location = match.group(1).strip()
                location_lower = location.lower()

                # Direct match in our comprehensive location list
                if location_lower in self.locations_lower:
                    return self.locations_lower[location_lower]

                # Partial match for cities/states
                for loc_lower, loc_proper in self.locations_lower.items():
                    if location_lower in loc_lower or loc_lower in location_lower:
                        return loc_proper

                # If it looks like a valid location but not in our list, return as-is
                if (
                    len(location) > 2
                    and location.replace(" ", "")
                    .replace(",", "")
                    .replace(".", "")
                    .isalpha()
                ):
                    return location.title()

        return None
