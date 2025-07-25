"""天翼云盘认证客户端"""

import re
import json
import time
from typing import Dict, Any, Optional, Tuple
from urllib.parse import urlencode

from loguru import logger
from utils.http_client import http_client

from .const import *
from .error import *
from .types import *
from .util import rsa_encrypt

class CloudAuthClient:
    """天翼云盘认证客户端"""

    def __init__(self):
        """初始化认证客户端"""
        self.request = http_client

    async def get_encrypt_conf(self) -> Dict[str, Any]:
        """
        获取加密参数
        :return: 包含公钥和前缀的字典
        """
        response = await self.request.post(
            f"{AUTH_URL}/api/logbox/config/encryptConf.do"
        )
        data = json.loads(response)
        return data.get("data", {})

    async def get_login_form(self) -> LoginFormCache:
        """
        获取登录表单参数
        :return: 登录表单缓存
        """
        params = {
            "appId": APP_ID,
            "clientType": CLIENT_TYPE,
            "returnURL": RETURN_URL,
            "timeStamp": int(time.time() * 1000)
        }
        
        response = await self.request.get(
            f"{WEB_URL}/api/portal/unifyLoginForPC.action",
            params=params,
        )
        
        # 解析响应文本中的参数
        captcha_token = re.search(r"'captchaToken' value='(.+?)'", response).group(1)
        lt = re.search(r"lt = \"(.+?)\"", response).group(1)
        param_id = re.search(r"paramId = \"(.+?)\"", response).group(1)
        req_id = re.search(r"reqId = \"(.+?)\"", response).group(1)
        
        return {
            "captcha_token": captcha_token,
            "lt": lt,
            "param_id": param_id,
            "req_id": req_id
        }

    def _build_login_form(
        self,
        encrypt_conf: Dict[str, Any],
        login_form: LoginFormCache,
        username: str,
        password: str
    ) -> Dict[str, Any]:
        """
        构建登录表单数据
        :param encrypt_conf: 加密配置
        :param login_form: 登录表单缓存
        :param username: 用户名
        :param password: 密码
        :return: 登录表单数据
        """
        # 加密用户名和密码
        pub_key = encrypt_conf["pubKey"]
        prefix = encrypt_conf["pre"]
        username_encrypt = rsa_encrypt(pub_key, username)
        password_encrypt = rsa_encrypt(pub_key, password)
        
        return {
            "appKey": APP_ID,
            "accountType": ACCOUNT_TYPE,
            # "mailSuffix": "@189.cn",
            "validateCode": "",
            "captchaToken": login_form["captcha_token"],
            "dynamicCheck": "FALSE",
            "clientType": "1",
            "cb_SaveName": "3",
            "isOauth2": False,
            "returnUrl": RETURN_URL,
            "paramId": login_form["param_id"],
            "userName": f"{prefix}{username_encrypt}",
            "password": f"{prefix}{password_encrypt}"
        }

    async def get_session_for_pc(
        self,
        redirect_url: Optional[str] = None,
        access_token: Optional[str] = None
    ) -> TokenSession:
        """
        获取PC端会话
        :param redirect_url: 重定向URL
        :param access_token: 访问令牌
        :return: 会话信息
        """
        params = {
            "appId": APP_ID,
            **get_client_suffix()
        }
        
        if redirect_url:
            params["redirectURL"] = redirect_url
        if access_token:
            params["accessToken"] = access_token
            
        response = await self.request.post(
            f"{API_URL}/getSessionForPC.action",
            params=params
        )
        logger.info(f"获取会话响应: {response}")
        
        # 响应是XML格式,需要解析为字典
        if isinstance(response, str) and response.startswith("<?xml"):
            # 简单解析XML获取关键字段
            session = {}
            for field in ["sessionKey", "sessionSecret", "accessToken", "refreshToken"]:
                match = re.search(f"<{field}>(.+?)</{field}>", response)
                if match:
                    session[field.lower()] = match.group(1)
            return session
            
        return json.loads(response)

    async def login_by_password(self, username: str, password: str) -> TokenSession:
        """
        使用用户名密码登录
        :param username: 用户名
        :param password: 密码
        :return: 会话信息
        """
        try:
            # 1. 获取加密配置和登录表单
            encrypt_conf = await self.get_encrypt_conf()
            login_form = await self.get_login_form()
            # 2. 构建并提交登录表单
            form_data = self._build_login_form(
                encrypt_conf,
                login_form,
                username,
                password
            )
            headers = {
                "Referer": AUTH_URL,
                "lt": login_form["lt"],
                "reqid": login_form["req_id"],
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            response = await self.request.post(
                f"{AUTH_URL}/api/logbox/oauth2/loginSubmit.do",
                data=form_data,
                headers=headers,
            )
            login_result = json.loads(response)
            logger.info(f"登录结果: {login_result}")
            
            # 3. 获取会话信息
            return await self.get_session_for_pc(redirect_url=login_result["toUrl"])
            
        except Exception as e:
            logger.error(f"登录失败: {str(e)}")
            raise AuthError(f"登录失败: {str(e)}")

    async def login_by_access_token(self, access_token: str) -> TokenSession:
        """
        使用访问令牌登录
        :param access_token: 访问令牌
        :return: 会话信息
        """
        return await self.get_session_for_pc(access_token=access_token)

    async def login_by_sson_cookie(self, cookie: str) -> TokenSession:
        """
        使用SSO Cookie登录
        :param cookie: SSO Cookie
        :return: 会话信息
        """
        params = {
            "appId": APP_ID,
            "clientType": CLIENT_TYPE,
            "returnURL": RETURN_URL,
            "timeStamp": int(time.time() * 1000)
        }
        
        # 1. 获取重定向URL
        response = await self.request.get(
            f"{WEB_URL}/api/portal/unifyLoginForPC.action",
            params=params,
            headers={
                "Content-Type": "application/x-www-form-urlencoded"
            }
        )
        
        # 2. 带Cookie访问重定向URL
        headers = {"Cookie": f"SSON={cookie}"}
        redirect_response = await self.request.get(
            response.url,
            headers=headers,
            follow_redirects=False
        )
        
        # 3. 获取会话信息
        return await self.get_session_for_pc(redirect_url=redirect_response.headers["location"])

    async def refresh_token(self, refresh_token: str) -> RefreshTokenSession:
        """
        刷新访问令牌
        :param refresh_token: 刷新令牌
        :return: 新的会话信息
        """
        form_data = {
            "clientId": APP_ID,
            "refreshToken": refresh_token,
            "grantType": "refresh_token",
            "format": "json"
        }
        
        response = await self.request.post(
            f"{AUTH_URL}/api/oauth2/refreshToken.do",
            data=form_data
        )
        return json.loads(response) 