import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    SNYK_TOKEN:   str = os.getenv("SNYK_TOKEN", "")
    SNYK_ORG_ID:  str = os.getenv("SNYK_ORG_ID", "")
    GITHUB_PAT:   str = os.getenv("GITHUB_PAT", "")
    PROXY_URL:    str = os.getenv("PROXY_URL", "")
    SSL_CERT:     str = os.getenv("SSL_CERT", "true")
    SNYK_TIMEOUT: int = int(os.getenv("SNYK_TIMEOUT", "60"))
    BACKEND_URL:  str = os.getenv("BACKEND_URL", "http://localhost:8000")

    @property
    def ssl_verify(self):
        # type: () -> object
        if self.SSL_CERT.lower() == "true":
            return True
        if self.SSL_CERT.lower() == "false":
            return False
        return self.SSL_CERT   # path to .pem

settings = Settings()