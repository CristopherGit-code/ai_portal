from dotenv import load_dotenv
load_dotenv()
import uuid
from langfuse import Langfuse
from langfuse.langchain import CallbackHandler
from .config.config import Settings

class FuseConfig:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FuseConfig,cls).__new__(cls)
            cls._instance._init()
        return cls._instance
    
    def _init(self):
        if self._initialized:
            return
        self.settings = Settings(r"C:\Users\Cristopher Hdz\Desktop\ai_portal\modules\util\config\config.yaml")   
        """ VM host """
        Langfuse(
            public_key=self.settings.langfuse.PUBLIC_VM_KEY,
            secret_key=self.settings.langfuse.SECRET_VM_KEY,
            host=self.settings.langfuse.VM_HOST
        )
        self.langfuse_handler = CallbackHandler()
        self._initialized = True

    def get_handler(self):
        return self.langfuse_handler
    
    def generate_id(self)->str:
        return str(uuid.uuid4())