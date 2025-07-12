metadatas = [
    {
        "id": profile["id"],
        "name": profile["name"],
        "email": profile.get("email"),
        "skills": ", ".join(profile.get("skills", [])),
        "experience_years": profile.get("experience_years", 0),
        "location": profile.get("location", "Unknown"),
    }
]
