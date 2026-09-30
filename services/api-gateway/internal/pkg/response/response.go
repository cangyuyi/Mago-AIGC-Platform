package response

import (
	"net/http"
	"strconv"

	"github.com/gin-gonic/gin"
)

type Response struct {
	Code    int         `json:"code"`
	Message string      `json:"message"`
	Data    interface{} `json:"data,omitempty"`
}

func Success(c *gin.Context, data interface{}) {
	if c.Writer.Written() {
		// A response has already been committed (for example an earlier 401);
		// never write a second header/body for the same request.
		return
	}
	c.JSON(http.StatusOK, Response{
		Code:    0,
		Message: "ok",
		Data:    data,
	})
}

func Error(c *gin.Context, httpStatus int, code int, message string) {
	if c.Writer.Written() {
		return
	}
	c.AbortWithStatusJSON(httpStatus, Response{
		Code:    code,
		Message: message,
	})
}

func BadRequest(c *gin.Context, message string) {
	Error(c, http.StatusBadRequest, 40000, message)
}

func Unauthorized(c *gin.Context, message string) {
	Error(c, http.StatusUnauthorized, 40100, message)
}

func Conflict(c *gin.Context, message string) {
	Error(c, http.StatusConflict, 40900, message)
}

func Forbidden(c *gin.Context, message string) {
	Error(c, http.StatusForbidden, 40300, message)
}

func NotFound(c *gin.Context, message string) {
	Error(c, http.StatusNotFound, 40400, message)
}

func InternalError(c *gin.Context, _ string) {
	// Never expose database, filesystem, or provider errors to clients. The
	// original error should be logged by the handler/service layer.
	Error(c, http.StatusInternalServerError, 50000, "internal server error")
}

// Paginated returns a paginated response
type PaginatedData struct {
	Items    interface{} `json:"items"`
	Total    int64       `json:"total"`
	Page     int         `json:"page"`
	PageSize int         `json:"page_size"`
}

func Paginated(c *gin.Context, items interface{}, total int64, page, pageSize int) {
	Success(c, PaginatedData{
		Items:    items,
		Total:    total,
		Page:     page,
		PageSize: pageSize,
	})
}

// GetPagination extracts pagination params from query
func GetPagination(c *gin.Context) (page, pageSize int) {
	page, _ = strconv.Atoi(c.DefaultQuery("page", "1"))
	pageSize, _ = strconv.Atoi(c.DefaultQuery("page_size", "20"))
	if page < 1 {
		page = 1
	}
	if pageSize < 1 || pageSize > 100 {
		pageSize = 20
	}
	return
}
