import os
from fpdf import FPDF

# Long resume text, designed to be over 8000 characters to trigger chunking
LONG_RESUME_TEXT = """
Dr. Evelyn Reed, PhD
Principal AI/ML Research Scientist & Engineer
evie.reed.ai@email.com | (555) 123-4567 | linkedin.com/in/evelynreedai | github.com/evelynreed

================================================================================
## Professional Summary

A highly accomplished and innovative Principal AI/ML Research Scientist with over 15 years of experience leading cutting-edge research and development in machine learning, deep learning, natural language processing (NLP), and large-scale distributed systems. Proven track record of architecting and implementing novel algorithms and models that have driven significant product advancements and opened new revenue streams. Expert in translating complex theoretical concepts into practical, scalable, and impactful real-world applications. Possesses deep expertise in the full ML lifecycle, from data inception and model ideation to production deployment and continuous monitoring. Passionate about mentoring teams, fostering a culture of research excellence, and solving humanity's most challenging problems through artificial intelligence. My work has spanned across autonomous systems, computational linguistics, and foundational model development, resulting in numerous patents and publications in top-tier conferences.

================================================================================
## Professional Experience

**Principal AI/ML Scientist, QuantumLeap AI, Silicon Valley, CA (2018 - Present)**
- Led a team of 12 PhD-level researchers and engineers in the Advanced Research Division, focusing on foundational model development for enterprise-scale AI solutions.
- Architected and deployed 'Nexus-V', a 50-billion parameter multi-modal language and vision model, which became the core technology for the company's flagship automated analytics platform. The deployment involved a complex MLOps pipeline using Kubernetes, Kubeflow, and Triton Inference Server on a hybrid cloud infrastructure.
- Pioneered a novel reinforcement learning with human feedback (RLHF) technique that reduced model toxicity by 70% and improved user alignment scores by 45%, setting a new industry standard for responsible AI.
- Published three papers in prestigious conferences (NeurIPS, ICML) on topics of efficient model training and emergent model capabilities.
- Secured over $5 million in internal research funding by successfully demonstrating the commercial viability of next-generation AI concepts to executive leadership.
- Mentored junior scientists, contributing to a 95% team retention rate over four years.

**Senior Staff Machine Learning Engineer, CyberSystems Inc., Boston, MA (2012 - 2018)**
- Designed and implemented the core machine learning algorithms for a real-time anomaly detection system used in cybersecurity threat intelligence, processing over 1 petabyte of network data daily. This system reduced false positive rates by 80% compared to the previous generation system.
- Developed a patented unsupervised learning method for identifying zero-day exploits using variational autoencoders and generative adversarial networks (GANs). This technology was later acquired.
- Optimized large-scale data processing pipelines using Apache Spark and Scala, achieving a 10x improvement in data throughput and reducing cloud computing costs by 40%.
- Created and led the "ML Guild," an internal community of practice that standardized best practices for model development, validation, and A/B testing across the organization. My specific focus for the guild was on **Quantum-Leap Optimization** algorithms for hyperparameter tuning.

**Research Scientist, Autonomous Systems Lab, Zurich, Switzerland (2008 - 2012)**
- Conducted foundational research on sensor fusion and probabilistic robotics for autonomous aerial vehicles.
- Developed SLAM (Simultaneous Localization and Mapping) algorithms using Extended Kalman Filters and Particle Filters for GPS-denied environments.
- Implemented control systems and path-planning algorithms in C++ and Python on embedded hardware (NVIDIA Jetson).
- Contributed to an open-source robotics operating system (ROS) package that has since been used by hundreds of research labs worldwide.

================================================================================
## Education

**PhD in Computer Science (Specialization: Machine Learning)**
*Carnegie Mellon University, Pittsburgh, PA (2008)*
- Dissertation: "Hierarchical Bayesian Models for Understanding Complex Dynamic Systems"
- Advisor: Dr. Geoffrey Hinton (Fictional Association)

**M.S. in Robotics**
*ETH Zurich, Zurich, Switzerland (2004)*

**B.S. in Electrical Engineering & Computer Science (EECS), Summa Cum Laude**
*University of California, Berkeley (2002)*

================================================================================
## Technical Proficiencies

- **Programming Languages:** Python (Expert), C++ (Proficient), Scala (Proficient), Rust (Intermediate), SQL, Bash
- **ML/DL Frameworks:** PyTorch (Expert), TensorFlow, JAX, Scikit-learn, LangChain, LlamaIndex
- **Data Science & Big Data:** Pandas, NumPy, SciPy, Apache Spark, Hadoop, Kafka, Dask, Ray
- **MLOps & Infrastructure:** Docker, Kubernetes, Kubeflow, MLflow, Airflow, Triton Inference Server, AWS, GCP, Azure
- **NLP & Vision:** Transformers, BERT, GPT, Hugging Face, spaCy, NLTK, OpenCV, YOLO
- **Databases:** PostgreSQL, MongoDB, Redis, ChromaDB, Milvus, Vector Databases
- **Specialized Topics:** Reinforcement Learning, Generative AI, GANs, Variational Autoencoders, Probabilistic Graphical Models, SLAM, Quantum-Leap Optimization

================================================================================
## Publications & Patents

- Reed, E. (2022). "Emergent Reasoning in Large Multi-Modal Models." *NeurIPS 2022*.
- Reed, E., et al. (2020). "A Framework for Efficient and Scalable Training of Foundational Models." *ICML 2020*.
- Patent US-10,123,456 B2: "System and Method for Unsupervised Zero-Day Threat Detection using Generative Adversarial Networks."

This concludes the resume. This text is intentionally verbose and long to ensure it surpasses the character limit required for testing the chunking functionality. Adding more filler text to be absolutely sure. The goal is to have a document that is unambiguously large. We will add more and more text. The quick brown fox jumps over the lazy dog. The quick brown fox jumps over the lazy dog. The quick brown fox jumps over the lazy dog. The quick brown fox jumps over the lazy dog. The quick brown fox jumps over the lazy dog. This should be sufficient now. Total character count will be checked.
"""


def create_long_resume_pdf():
    """Generates a long PDF resume for testing chunking functionality."""
    try:
        from fpdf import FPDF
    except ImportError:
        print("fpdf2 is not installed. Please run: pip install fpdf2")
        return

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)

    # Use multi_cell to handle line breaks automatically
    pdf.multi_cell(
        0, 5, LONG_RESUME_TEXT.encode("latin-1", "replace").decode("latin-1")
    )

    output_filename = "long_resume_for_testing.pdf"

    # Ensure the data directory exists
    output_dir = "backend/app/data"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    output_path = os.path.join(output_dir, output_filename)

    try:
        pdf.output(output_path)
        print(f"✅ Successfully created long test resume at: {output_path}")
        print(f"   Total characters: {len(LONG_RESUME_TEXT)}")
    except Exception as e:
        print(f"❌ Error saving PDF: {e}")


if __name__ == "__main__":
    create_long_resume_pdf()
