"""
Adapter to make the server-based controller compatible with LangChain
This allows using the original langchain_integration.py code with minimal changes
"""

from langchain.llms.base import LLM
from typing import Any, List, Optional
from pydantic import Field
import asyncio


class LlamaServerLLM(LLM):
    """
    LangChain-compatible wrapper for our server-based LLM controller
    
    This allows the controller to be used with LangChain chains, agents, etc.
    just like the original llama-cpp-python based version.
    """
    
    controller: Any = Field(exclude=True)
    npc_id: str = "default"
    
    class Config:
        arbitrary_types_allowed = True
    
    def __init__(self, controller, npc_id: str = "default", **kwargs):
        super().__init__(**kwargs)
        self.controller = controller
        self.npc_id = npc_id
    
    @property
    def _llm_type(self) -> str:
        return "llama-server"
    
    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> str:
        """Synchronous call - LangChain sometimes uses this"""
        # Run async method synchronously
        return asyncio.get_event_loop().run_until_complete(
            self.controller.generate(prompt, self.npc_id, **kwargs)
        )
    
    async def _acall(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> str:
        """Async call - preferred"""
        return await self.controller.generate(prompt, self.npc_id, **kwargs)


# Modify the original controller to have LangChain compatibility
def add_langchain_compatibility(controller):
    """
    Add a langchain_llm property to the controller
    This allows using it like: controller.langchain_llm
    """
    controller.langchain_llm = LlamaServerLLM(controller)
    return controller


# Example usage:
"""
from llm_controller_server import LLMController
from langchain_server_adapter import add_langchain_compatibility

# Create controller
controller = LLMController(model_path="models/your-model.gguf")
await controller.start()

# Add LangChain compatibility
add_langchain_compatibility(controller)

# Now can use with LangChain
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate

prompt = PromptTemplate(
    input_variables=["question"],
    template="You are a helpful NPC. {question}"
)

chain = LLMChain(llm=controller.langchain_llm, prompt=prompt)
response = chain.run("What do you sell?")
"""
