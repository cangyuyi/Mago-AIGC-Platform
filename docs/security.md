# 安全说明

## 已实现的安全措施
1. **传输安全**：生产环境强制HTTPS，HSTS头开启
2. **认证**：JWT token认证，默认 access token 有效期 15 分钟、refresh token 有效期 7 天；生产环境应通过 `JWT_ACCESS_TTL_MINUTES` 和 `JWT_REFRESH_TTL_DAYS` 明确配置
3. **授权**：所有API校验用户身份，用户只能访问自己的项目数据
4. **限流**：
   - 全局200rps限制
   - 登录/注册接口5rps/IP防暴力破解
   - 已认证用户50rps/IP
5. **输入校验**：所有请求参数校验，请求体大小限制10MB
6. **安全头**：X-Frame-Options/X-Content-Type-Options/X-XSS-Protection/Referrer-Policy
7. **SQL注入防护**：GORM参数化查询，避免SQL拼接
8. **CORS**：生产环境严格配置允许的Origin，不使用*
9. **审计日志**：当前仅保留结构化运行日志，完整的敏感操作审计日志尚未实现；生产部署不能把现有日志当作合规审计记录

## 生产环境必须做
1. 所有默认密码全部修改，使用强密码
2. JWT_SECRET使用32位以上随机字符串
3. 数据库/Redis/MinIO等服务不对外暴露端口
4. 开启WAF防护，拦截常见攻击
5. 定期备份数据库并演练恢复流程
6. 定期更新依赖版本修复安全漏洞
7. 配置日志审计留存至少30天
