from logic.prompt import CONSISTENCY_PROMPT


def classify(content: str, book_name: str, document_store, llm) -> str:
    """
    Classify whether a backstory is consistent with a novel.
    
    Args:
        content: The hypothetical backstory text
        book_name: Name of the novel
        document_store: SynchronousDocumentStore instance
        llm: LiteLLM Chat instance
        
    Returns:
        str: Response containing Label and Reason
    """
    try:
        # Retrieve relevant passages from the novel
        docs = document_store.retrieve(
            query=f"{content} {book_name}",
            k=10,
        )

        if docs and len(docs) > 0:
            evidence = "\n\n---\n\n".join(d.text[:500] for d in docs)  # Limit each chunk
        else:
            evidence = "No evidence retrieved from the novel."

        prompt = f"""{CONSISTENCY_PROMPT}

Novel: {book_name}

Retrieved Evidence:
{evidence}

Hypothetical Backstory:
{content}

Respond strictly in this format:
Label: 0 or 1
Reason: explanation
"""

        # Call LLM - LiteLLMChat expects a list of messages
        response = llm([
            {"role": "user", "content": prompt}
        ])
        
        # Extract text from response
        if isinstance(response, dict):
            response_text = response.get('content') or response.get('text') or str(response)
        elif isinstance(response, str):
            response_text = response
        else:
            response_text = str(response)
        
        return response_text
        
    except Exception as e:
        print(f"❌ Classification error: {e}")
        return f"Label: 0\nReason: LLM error: {str(e)}"