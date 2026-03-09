from repo_analyzer.java_parser import JavaClassInfo


TARGET_ANNOTATIONS = {"Service", "Controller", "RestController", "Component"}


def filter_target_classes(classes: list[JavaClassInfo]) -> list[JavaClassInfo]:
    filtered: list[JavaClassInfo] = []
    for c in classes:
        if TARGET_ANNOTATIONS.intersection(set(c.annotations)):
            filtered.append(c)
            continue

        # Include utility classes with non-trivial methods.
        if len(c.methods) >= 2 and not c.class_name.endswith(("Dto", "Entity", "Model")):
            filtered.append(c)

    return filtered
