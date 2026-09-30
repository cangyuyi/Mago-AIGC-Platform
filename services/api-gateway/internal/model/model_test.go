package model

import (
	"encoding/json"
	"reflect"
	"testing"
)

func TestJSONValueSupportsObjectAndArray(t *testing.T) {
	cases := []string{
		`{"score":0.95}`,
		`[{"url":"https://example.com/a.png"},"character"]`,
		`"plain string"`,
	}

	for _, input := range cases {
		var value JSONValue
		if err := value.Scan([]byte(input)); err != nil {
			t.Fatalf("Scan(%s): %v", input, err)
		}
		stored, err := value.Value()
		if err != nil {
			t.Fatalf("Value(%s): %v", input, err)
		}
		var got interface{}
		if err := json.Unmarshal(stored.([]byte), &got); err != nil {
			t.Fatalf("unmarshal stored value %s: %v", input, err)
		}
		var want interface{}
		if err := json.Unmarshal([]byte(input), &want); err != nil {
			t.Fatal(err)
		}
		if !reflect.DeepEqual(got, want) {
			t.Errorf("round trip mismatch: got %#v, want %#v", got, want)
		}
	}
}

func TestJSONValueMarshalJSONPreservesArrayShape(t *testing.T) {
	value := JSONValue{Data: []string{"a", "b"}}
	encoded, err := json.Marshal(value)
	if err != nil {
		t.Fatal(err)
	}
	if string(encoded) != `["a","b"]` {
		t.Fatalf("encoded %s as object instead of array", encoded)
	}
}
