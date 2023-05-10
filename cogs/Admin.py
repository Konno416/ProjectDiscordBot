import discord
from discord.ext import commands
from discord import FFmpegPCMAudio
from discord import member
from discord import *
from discord.ext.commands import has_permissions, MissingPermissions
import requests
import json
import os
from dotenv import load_dotenv
import wavelink
import mysql.connector
from mysql.connector import Error
from datetime import datetime
from datetime import date

load_dotenv()

SERVERID = os.getenv("SERVERID")

#Have to make your own profane list in an array in the env file.
# profane = os.getenv("PROFANE")

class Admin(commands.Cog):
    def __init__(self, client: commands.Bot):
        self.client = client

    @commands.Cog.listener()
    async def on_ready(self):
        print("Admin.py is ready!")

    @commands.Cog.listener()
    async def on_message(self, message):
        profane = os.getenv("PROFANE_WORDS").split(",")
        if message.author.bot:
            return  # ignore messages from bots
        for word in profane:
            if word in message.content.lower():
                await message.delete()
                user = message.author
                await user.send("Don't use profanity in this server or else!")
                break  # stop checking for profanity once one is found
        await self.client.process_commands(message)


    # Causes an error where the bot does not respond
    @app_commands.command(name="clear", description="Should clear the amount of messages inputed or just typing all should delete everything")
    @has_permissions(manage_messages=True)
    async def clear(self, interaction: discord.Interaction, amount:str):
        await interaction.channel.purge(limit=(int(amount) + 1))
        await interaction.response.send(f"Cleared {amount} from the channel!", ephemeral=True)
        

    @commands.command()
    @has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason=None):
        await member.kick(reason=reason)
        await ctx.send(f'User {member} has been kicked')

    @kick.error
    async def kick_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You don't have permission to kick people!")


    @commands.command()
    @has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason=None):
        await member.ban(reason=reason)
        await ctx.send(f'User {member} has been banned')

    @ban.error
    async def ban_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("You don't have permission to kick people!")


    # @client.event()
    # async def on_command_error(interaction: discord.Interaction, error):
    #     if isinstance(error, commands.MissingPermissions):
    #         await interaction.response.send_message("You don't ahve permission to run this command")

    @app_commands.command(name="store_info", description="Test for storing data")
    async def store_info(self, interaction: discord.Interaction, message: str):
        
        guild = interaction.guild.id

        try:
            connection = mysql.connector.connect(host='localhost',
                                                 database = 'tutorial_bot',
                                                 user = 'root',
                                                 password = 'root')
            
            mySql_Create_Table_Query = """CREATE TABLE DB_""" + str(guild) + """ (
                                        Id int(11) NOT NULL AUTO_INCREMENT,
                                        User varchar(250) NOT NULL,
                                        Message varchar(5000) NOT NULL,
                                        PRIMARY KEY(Id)) """    
            
            cursor = connection.cursor()
            result = cursor.execute(mySql_Create_Table_Query)
            print("Guild (" + str(guild) + ") Table created successfully")

        except mysql.connector.Error as error:
            print("Failed to create table in MySQL: {}".format(error))
        
        finally:
            if connection.is_connected():

                table = "DB_" + str(guild)

                mySql_Insert_Row_Query = "INSERT INTO " + table + " (User, Message) VALUES (%s, %s)"
                mySql_Insert_Row_Values = (str(interaction.user), message)

                cursor.execute(mySql_Insert_Row_Query, mySql_Insert_Row_Values)
                connection.commit()

                await interaction.response.send_message("I have stored your message for you!")

                cursor.close()
                connection.close()
                print("Mysql connection has been closed")


    @app_commands.command(name="retrieve_info", description="Retrieve some data that a user has stored")
    async def retrieve_info(self, interaction: discord.Interaction):

        guild = interaction.guild.id
        table = "DB_" + str(guild)

        try:
            connection = mysql.connector.connect(host='localhost',
                                                 database = 'tutorial_bot',
                                                 user = 'root',
                                                 password = 'root')
            
            cursor = connection.cursor()

            sql_select_query = "Select * from " + table + " where user like '" + str(interaction.user) + "'"

            cursor.execute(sql_select_query)

            record = cursor.fetchall()

            Recieved_Data = []

            for row in record:
                Recieved_Data.append({"Id": str(row[0]), "Message": str(row[2])})

            await interaction.response.send_message("All Stored Data: \n \n " + json.dumps(Recieved_Data, indent=1))

        except mysql.connector.Error as error:
            print("Failed to get record from MySQL table: {}".format(error))

        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
                print("Mysql connection is closed")


    @app_commands.command(name="statistics", description="Shows the statistics for a selected user")
    async def statistics(self, interaction: discord.Interaction, user: discord.Member):

        pic = user.avatar.url

        try:
            connection = mysql.connector.connect(host='localhost',
                                                 database = 'tutorial_bot',
                                                 user = 'root',
                                                 password = 'root')
            
            cursor = connection.cursor()

            sql_select_query = "Select * from Users where user like '" + str(user) + "'"

            cursor.execute(sql_select_query)

            record = cursor.fetchone()

            print(record)

            if(record == None):
                await interaction.response.send_message("There is no data on this individual!", ephemeral=True)
            
            embed = discord.Embed(
            color=discord.Color.dark_blue(),
            title="Stats", 
            description=f"Statistics of {user}!"    
            )
            embed.add_field(name="ID: ", value=record[0])
            embed.add_field(name="Name: ", value=record[1])
            embed.add_field(name="Joined: ", value=record[2])
            embed.set_thumbnail(url=pic)

            
            await interaction.response.send_message(embed=embed, ephemeral=True)

        except mysql.connector.Error as error:
            print("Failed to get record from MySQL table: {}".format(error))

        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
                print("Mysql connection is closed")


    @app_commands.command(name="add_user", description="Adds a user to the stats Database if they are not in it already!")
    async def add_user_DB(self, interaction: discord.Interaction, user: discord.Member):

        pic = user.avatar.url
        name = user.name
        pic = user.display_avatar.url
        memberId = user.id
        joined = user.joined_at.date()

        try:
            connection = mysql.connector.connect(host='localhost',
                                                 database = 'tutorial_bot',
                                                 user = 'root',
                                                 password = 'root')
            
            cursor = connection.cursor()

            sql_select_query = "Select * from Users where user like '" + str(user) + "'"

            cursor.execute(sql_select_query)

            record = cursor.fetchone()

            print(record)

            if(record == None):
                mySql_Insert_Row_Query = "INSERT INTO `users` (`Id`, `User`, `Joinedat`) VALUES (%s, %s, %s);"
                mySql_Insert_Row_Value = (str(memberId), str(user), str(joined))

                cursor.execute(mySql_Insert_Row_Query, mySql_Insert_Row_Value)
                connection.commit()

                await interaction.response.send_message("Added user to the database!", ephemeral=True)

            else:
                await interaction.response.send_message("User is already in the database!", ephemeral=True)

        except mysql.connector.Error as error:
            print("Failed to get record from MySQL table: {}".format(error))

        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
                print("Mysql connection is closed")


    @app_commands.command(name="server_stats", description="Shows server stats!")
    async def server_stats(self, interaction: discord.Interaction):

        serverdate = interaction.guild.created_at.date()
        memberamount = interaction.guild.member_count
        serverid = interaction.guild.id
        pic = interaction.guild.icon.url

        # print(serverdate)
        # print(memberamount)
        # print(serverid)
        # print(f"picture = {pic}")
        

        embed = discord.Embed(
            color=discord.Color.blue(), 
            title="Server Statistics", 
            description="Here are some server Statistics"
            )
        embed.add_field(name="Server ID: ", value=serverid)
        embed.add_field(name="Member Amount: ", value=memberamount)
        embed.add_field(name="Server Created", value=serverdate)
        embed.set_thumbnail(url=pic)

        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    

async def setup(client):
    await client.add_cog(Admin(client), guilds=[discord.Object(id=SERVERID)])