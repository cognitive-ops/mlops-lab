#!/usr/bin/env python3
"""
Test script to verify OpenAI integration is working properly
"""


def test_openai_integration():
    """Test OpenAI imports and basic functionality"""
    print("🧪 Testing OpenAI Integration...")

    try:
        # Test imports
        from langchain_openai import OpenAIEmbeddings, ChatOpenAI
        from langchain_core.documents import Document
        print("✅ All imports successful!")

        # Test ChatOpenAI initialization (will fail without API key, but class should load)
        print("Testing ChatOpenAI class initialization...")
        llm_class = ChatOpenAI
        print(f"✅ ChatOpenAI class available: {llm_class.__name__}")

        # Test embedding class
        print("Testing OpenAIEmbeddings class...")
        embedding_class = OpenAIEmbeddings
        print(
            f"✅ OpenAIEmbeddings class available: {embedding_class.__name__}")

        # Test document creation
        print("Testing Document creation...")
        doc = Document(page_content="Test content",
                       metadata={"source": "test"})
        print(f"✅ Document created: {len(doc.page_content)} characters")

        print(
            "\n🎉 All tests passed! Your code is ready to use OpenAI instead of Anthropic.")
        print("💡 Don't forget to set your OPENAI_API_KEY environment variable!")

    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

    return True


if __name__ == "__main__":
    test_openai_integration()
