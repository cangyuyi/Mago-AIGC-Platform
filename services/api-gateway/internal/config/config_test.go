package config

import (
	"net/url"
	"os"
	"reflect"
	"strings"
	"testing"

	"gorm.io/driver/postgres"
	"gorm.io/gorm"
)

func TestDatabaseDSNEscapesCredentials(t *testing.T) {
	password := `p@ss:/?#%word with spaces\\and\"quotes`
	cfg := DatabaseConfig{
		Host:     "localhost",
		Port:     "5432",
		User:     "mago user",
		Password: password,
		DBName:   "mago",
		SSLMode:  "disable",
	}

	parsed, err := url.Parse(cfg.DSN())
	if err != nil {
		t.Fatalf("DSN() produced an invalid URL: %v", err)
	}
	gotPassword, ok := parsed.User.Password()
	if !ok || parsed.User.Username() != cfg.User || gotPassword != password {
		t.Fatalf("DSN() credentials did not round-trip: user=%q password=%q", parsed.User.Username(), gotPassword)
	}
	if parsed.Host != "localhost:5432" || parsed.Path != "/mago" {
		t.Fatalf("DSN() address = %q%s, want localhost:5432/mago", parsed.Host, parsed.Path)
	}
	if parsed.Query().Get("sslmode") != "disable" || parsed.Query().Get("TimeZone") != "Asia/Shanghai" {
		t.Fatalf("DSN() query = %v", parsed.Query())
	}
	if !strings.Contains(parsed.RawQuery, "TimeZone=Asia/Shanghai") {
		t.Fatalf("DSN() must preserve the literal timezone expected by GORM: %q", parsed.RawQuery)
	}
	if _, err := gorm.Open(postgres.Open(cfg.DSN()), &gorm.Config{DisableAutomaticPing: true}); err != nil {
		t.Fatalf("PostgreSQL driver rejected DSN(): %v", err)
	}
}

func TestGetAllowedOriginsUsesDefaultsWhenUnsetOrBlank(t *testing.T) {
	for _, raw := range []string{"", "   ", ",,,"} {
		t.Run(raw, func(t *testing.T) {
			t.Setenv("ALLOWED_ORIGINS", raw)
			want := []string{"http://localhost:3000", "http://localhost"}
			if got := getAllowedOrigins(); !reflect.DeepEqual(got, want) {
				t.Fatalf("getAllowedOrigins() = %#v, want %#v", got, want)
			}
		})
	}
}

func TestGetAllowedOriginsTrimsAndFiltersValues(t *testing.T) {
	t.Setenv("ALLOWED_ORIGINS", " https://example.com, ,http://localhost:3000 ")
	want := []string{"https://example.com", "http://localhost:3000"}
	if got := getAllowedOrigins(); !reflect.DeepEqual(got, want) {
		t.Fatalf("getAllowedOrigins() = %#v, want %#v", got, want)
	}
}

func TestGetAllowedOriginsDoesNotDependOnProcessEnvironmentAfterSetenv(t *testing.T) {
	old, had := os.LookupEnv("ALLOWED_ORIGINS")
	t.Cleanup(func() {
		if had {
			_ = os.Setenv("ALLOWED_ORIGINS", old)
		} else {
			_ = os.Unsetenv("ALLOWED_ORIGINS")
		}
	})
	_ = os.Setenv("ALLOWED_ORIGINS", "https://example.org")
	if got := getAllowedOrigins(); len(got) != 1 || got[0] != "https://example.org" {
		t.Fatalf("getAllowedOrigins() = %#v", got)
	}
}

func TestValidateProductionConfigRejectsBlankAndWildcardOrigins(t *testing.T) {
	cfg := &Config{JWT: JWTConfig{Secret: "this-is-a-random-secret-with-at-least-32-chars"}}
	for _, raw := range []string{"", "   ", ",,,", "*", "https://*.example.com"} {
		t.Run(raw, func(t *testing.T) {
			if err := validateProductionConfig(cfg, raw); err == nil {
				t.Fatalf("validateProductionConfig(%q) unexpectedly succeeded", raw)
			}
		})
	}
}

func TestValidateProductionConfigAcceptsExplicitOrigins(t *testing.T) {
	cfg := &Config{JWT: JWTConfig{Secret: "this-is-a-random-secret-with-at-least-32-chars"}}
	if err := validateProductionConfig(cfg, "https://app.example.com, https://admin.example.com"); err != nil {
		t.Fatalf("validateProductionConfig() unexpected error: %v", err)
	}
}
