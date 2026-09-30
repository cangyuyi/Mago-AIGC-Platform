package config

import (
	"fmt"
	"log"
	"net"
	"net/url"
	"os"
	"strconv"
	"strings"

	"github.com/joho/godotenv"
)

type Config struct {
	Server   ServerConfig
	Database DatabaseConfig
	Redis    RedisConfig
	MinIO    MinIOConfig
	JWT      JWTConfig
	Agent    AgentConfig
	App      AppConfig
}

type ServerConfig struct {
	Port           string
	Env            string
	AllowedOrigins []string
}

type DatabaseConfig struct {
	Host     string
	Port     string
	User     string
	Password string
	DBName   string
	SSLMode  string
}

func (d DatabaseConfig) DSN() string {
	connectionURL := url.URL{
		Scheme: "postgres",
		Host:   net.JoinHostPort(d.Host, d.Port),
		Path:   "/" + d.DBName,
		User:   url.UserPassword(d.User, d.Password),
	}
	query := url.Values{}
	query.Set("sslmode", d.SSLMode)
	// Keep TimeZone's slash literal because GORM extracts this parameter from
	// the raw DSN before pgx parses the URL query.
	connectionURL.RawQuery = query.Encode() + "&TimeZone=Asia/Shanghai"
	return connectionURL.String()
}

type RedisConfig struct {
	Addr     string
	Password string
	DB       int
}

type MinIOConfig struct {
	Endpoint  string
	AccessKey string
	SecretKey string
	Bucket    string
	UseSSL    bool
}

type JWTConfig struct {
	Secret         string
	AccessTTLMin   int
	RefreshTTLDays int
}

type AgentConfig struct {
	BaseURL string
}

type AppConfig struct {
	Name    string
	Version string
}

func getEnv(key, defaultVal string) string {
	if val := os.Getenv(key); val != "" {
		return val
	}
	return defaultVal
}

func getEnvInt(key string, defaultVal int) int {
	if val := os.Getenv(key); val != "" {
		if n, err := strconv.Atoi(val); err == nil {
			return n
		}
	}
	return defaultVal
}

const defaultAllowedOrigins = "http://localhost:3000,http://localhost"

func parseAllowedOrigins(raw string) []string {
	origins := make([]string, 0, 2)
	for _, origin := range strings.Split(raw, ",") {
		if trimmed := strings.TrimSpace(origin); trimmed != "" {
			origins = append(origins, trimmed)
		}
	}
	return origins
}

func getAllowedOrigins() []string {
	origins := parseAllowedOrigins(os.Getenv("ALLOWED_ORIGINS"))
	if len(origins) == 0 {
		return strings.Split(defaultAllowedOrigins, ",")
	}
	return origins
}

func validateProductionConfig(cfg *Config, rawAllowedOrigins string) error {
	origins := parseAllowedOrigins(rawAllowedOrigins)
	if len(origins) == 0 {
		return fmt.Errorf("ALLOWED_ORIGINS must be set explicitly in production")
	}
	for _, origin := range origins {
		if strings.Contains(origin, "*") {
			return fmt.Errorf("ALLOWED_ORIGINS must not contain wildcard origins when credentials are enabled")
		}
	}
	weakSecrets := map[string]bool{
		"dev-secret-change-in-production":                     true,
		"dev_jwt_secret_change_in_prod":                       true,
		"change_this_to_a_secure_random_string_in_production": true,
	}
	if weakSecrets[cfg.JWT.Secret] || len(cfg.JWT.Secret) < 32 {
		return fmt.Errorf("JWT_SECRET must be a random string of at least 32 characters in production")
	}
	return nil
}

func Load() *Config {
	// Load the local file first, then the repository-level file used by native
	// development launches from services/api-gateway. Missing files are ignored
	// so Docker/production environment variables remain the source of truth.
	_ = godotenv.Load(".env", "../.env", "../../.env")

	return &Config{
		Server: ServerConfig{
			Port:           getEnv("API_PORT", getEnv("SERVER_PORT", "8080")),
			Env:            getEnv("SERVER_ENV", "development"),
			AllowedOrigins: getAllowedOrigins(),
		},
		Database: DatabaseConfig{
			Host:     getEnv("POSTGRES_HOST", "localhost"),
			Port:     getEnv("POSTGRES_PORT", "5432"),
			User:     getEnv("POSTGRES_USER", "mago"),
			Password: getEnv("POSTGRES_PASSWORD", "mago_secret"),
			DBName:   getEnv("POSTGRES_DB", "mago"),
			SSLMode:  getEnv("POSTGRES_SSLMODE", "disable"),
		},
		Redis: RedisConfig{
			Addr:     getEnv("REDIS_HOST", "localhost") + ":" + getEnv("REDIS_PORT", "6379"),
			Password: getEnv("REDIS_PASSWORD", ""),
			DB:       0,
		},
		MinIO: MinIOConfig{
			Endpoint: getEnv("MINIO_ENDPOINT", "localhost:9000"),
			// Accept the names used by MinIO itself as a fallback so native
			// launches and Compose launches use the same credentials.
			AccessKey: getEnv("MINIO_ACCESS_KEY", getEnv("MINIO_ROOT_USER", "magoadmin")),
			SecretKey: getEnv("MINIO_SECRET_KEY", getEnv("MINIO_ROOT_PASSWORD", "magoadmin123")),
			Bucket:    getEnv("MINIO_BUCKET", "mago-agent"),
			UseSSL:    getEnv("MINIO_SECURE", "false") == "true",
		},
		JWT: JWTConfig{
			Secret:         getEnv("JWT_SECRET", "dev-secret-change-in-production"),
			AccessTTLMin:   getEnvInt("JWT_ACCESS_TTL_MINUTES", 15),
			RefreshTTLDays: getEnvInt("JWT_REFRESH_TTL_DAYS", 7),
		},
		Agent: AgentConfig{
			BaseURL: getEnv("AGENT_BASE_URL", "http://localhost:8000"),
		},
		App: AppConfig{
			Name:    "mago-agent-api",
			Version: "0.1.0",
		},
	}
}

// MustLoad loads config and panics on critical validation failures.
func MustLoad() *Config {
	cfg := Load()
	if cfg.JWT.Secret == "" {
		log.Fatal("JWT_SECRET must be set")
	}
	if cfg.Server.Env == "production" {
		if err := validateProductionConfig(cfg, os.Getenv("ALLOWED_ORIGINS")); err != nil {
			log.Fatal(err)
		}
	} else {
		for _, origin := range cfg.Server.AllowedOrigins {
			if strings.Contains(origin, "*") {
				log.Fatal("ALLOWED_ORIGINS must not contain wildcard origins when credentials are enabled")
			}
		}
	}
	return cfg
}
