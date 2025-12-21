# iOS App Migration: Tags Support

This document outlines the required changes for the iOS app to support the new DataSource tags feature.

## API Changes

### DataSource Model

The `DataSource` API response now includes a `tags` field:

```json
{
  "id": "uuid",
  "name": "Stadt Gummersbach",
  "base_url": "https://gummersbach.de",
  "source_type": "WEBSITE",
  "tags": ["nrw", "kommunal", "de"],
  ...
}
```

### Required Model Updates

#### EntitySource.swift (or similar)

Add the tags property to your DataSource model:

```swift
struct EntitySource: Codable, Identifiable {
    let id: UUID
    let name: String
    let baseUrl: String
    let sourceType: String
    let tags: [String]?  // NEW: Optional array of tags
    // ... other properties
}
```

## UI Changes

### Tag Display in EntitySourceRow

Add tag chips to the source row view:

```swift
struct EntitySourceRow: View {
    let source: EntitySource

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(source.name)
                .font(.headline)

            Text(source.baseUrl)
                .font(.caption)
                .foregroundColor(.secondary)

            // NEW: Tag chips
            if let tags = source.tags, !tags.isEmpty {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 4) {
                        ForEach(tags, id: \.self) { tag in
                            TagChip(text: tag)
                        }
                    }
                }
            }
        }
    }
}

struct TagChip: View {
    let text: String

    var body: some View {
        Text(text)
            .font(.caption2)
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background(Color.blue.opacity(0.1))
            .foregroundColor(.blue)
            .cornerRadius(12)
    }
}
```

### Optional: Tag Filter UI

Add tag filtering to SourcesTabView:

```swift
struct SourcesTabView: View {
    @State private var selectedTags: Set<String> = []
    @State private var availableTags: [String] = []

    var filteredSources: [EntitySource] {
        guard !selectedTags.isEmpty else { return allSources }
        return allSources.filter { source in
            guard let sourceTags = source.tags else { return false }
            return !selectedTags.isDisjoint(with: Set(sourceTags))
        }
    }

    var body: some View {
        VStack {
            // Tag filter bar
            ScrollView(.horizontal, showsIndicators: false) {
                HStack {
                    ForEach(availableTags, id: \.self) { tag in
                        TagFilterChip(
                            text: tag,
                            isSelected: selectedTags.contains(tag),
                            onTap: { toggleTag(tag) }
                        )
                    }
                }
                .padding(.horizontal)
            }

            // Sources list
            List(filteredSources) { source in
                EntitySourceRow(source: source)
            }
        }
    }

    private func toggleTag(_ tag: String) {
        if selectedTags.contains(tag) {
            selectedTags.remove(tag)
        } else {
            selectedTags.insert(tag)
        }
    }
}
```

## API Endpoints

### Get Available Tags

```
GET /api/admin/sources/tags
```

Response:
```json
{
  "tags": ["de", "nrw", "bayern", "kommunal", "oparl", ...]
}
```

### Filter Sources by Tags

```
GET /api/admin/sources?tags=nrw,kommunal&tag_match=all
```

Parameters:
- `tags`: Comma-separated list of tags
- `tag_match`: `all` (AND) or `any` (OR)

## Tag Categories (Reference)

### Geographic Tags (Bundeslaender)
- nrw, bayern, baden-wuerttemberg, hessen, niedersachsen
- schleswig-holstein, rheinland-pfalz, saarland, berlin
- brandenburg, mecklenburg-vorpommern, sachsen, sachsen-anhalt, thueringen
- hamburg, bremen

### Country Tags
- de (Deutschland), at (Oesterreich), ch (Schweiz), uk (Grossbritannien)

### Type Tags
- kommunal, landkreis, landesebene, bundesebene
- oparl, ratsinformation

### Topic Tags
- windkraft, solar, bauen, verkehr, umwelt

## Testing

1. Verify tags are displayed in source list
2. Test tag filtering (if implemented)
3. Ensure app handles sources without tags (nil/empty array)
4. Test with various tag combinations

## Migration Checklist

- [ ] Update EntitySource model with `tags: [String]?`
- [ ] Add TagChip component
- [ ] Update EntitySourceRow to display tags
- [ ] (Optional) Add tag filter UI
- [ ] (Optional) Load available tags from API
- [ ] Test with production data
