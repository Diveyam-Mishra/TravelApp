async def fetchAllBugs(bugContainer):
    query = "SELECT * FROM c"
    
    search = list(bugContainer.query_items(
        query=query,
        enable_cross_partition_query=True
    ))

    return search